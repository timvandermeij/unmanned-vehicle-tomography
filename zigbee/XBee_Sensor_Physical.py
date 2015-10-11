# TODO: Implement _get_location() by querying the flight controller.
# TODO: Replace /dev/ttyUSB.
# TODO: Unit testing.

import serial
import json
import time
import random
from xbee import ZigBee
from XBee_Sensor import XBee_Sensor
from ..settings import Arguments, Settings

class XBee_Sensor_Physical(XBee_Sensor):
    STATUS_OK = "\x00"

    def __init__(self, sensor_id, settings, scheduler):
        """
        Initialize the sensor.
        """

        if isinstance(settings, Arguments):
            self.settings = settings.get_settings("xbee_sensor_physical")
        elif isinstance(settings, Settings):
            self.settings = settings
        else:
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        self.id = sensor_id
        self.scheduler = scheduler
        self._next_timestamp = self.scheduler.get_next_timestamp()
        self._serial_connection = None
        self._sensor = None
        self._address = None
        self._data = []

    def activate(self):
        """
        Activate the sensor by sending a packet if it is not a ground station.
        The sensor always receives packets asynchronously.
        """

        # Lazily initialize the serial connection and ZigBee object.
        if self._serial_connection == None and self._sensor == None:
            self._serial_connection = serial.Serial("/dev/ttyUSB{}".format(self.id - 1),
                                                    self.settings.get("baud_rate"))
            self._sensor = ZigBee(self._serial_connection, callback=self._receive)

            # Set this sensor's address.
            self._sensor.send("at", command="SH")
            self._sensor.send("at", command="SL")

        if self.id > 0 and time.time() >= self._next_timestamp:
            self._send()
            self._next_timestamp = self.scheduler.get_next_timestamp()

    def deactivate(self):
        """
        Deactivate the sensor and close the serial connection.
        """

        self._sensor.halt()
        self._serial_connection.close()

    def _send(self):
        """
        Send a packet to each other sensor in the network.
        """

        packet = {
            "from": self._get_location(),
            "from_id": self.id,
            "timestamp": time.time()
        }
        sensors = self.settings.get("sensors")
        for index, sensor_address in enumerate(sensors):
            # Unescape the string as it is escaped in JSON.
            sensor_address = sensor_address.decode("string_escape")

            # Do not send to yourself or the ground sensor.
            if sensor_address != self._address and index > 0:
                self._sensor.send("tx", dest_addr_long=sensor_address,
                                  dest_addr="\xFF\xFE", frame_id="\x01",
                                  data=json.dumps(packet))

        # Send the sweep data to the ground sensor and clear the list for the next round.
        ground_sensor_address = sensors[0].decode("string_escape")
        for packet in self._data:
            self._sensor.send("tx", dest_addr_long=ground_sensor_address,
                              dest_addr="\xFF\xFE", frame_id="\x01",
                              data=json.dumps(packet))

        self.data = []

    def _receive(self, packet):
        """
        Receive and process a received packet from another sensor in the network.
        """

        if self.id > 0:
            if packet["id"] == "rx":
                payload = json.loads(packet["rf_data"])

                # Synchronize the scheduler using the timestamp in the payload.
                self._next_timestamp = self.scheduler.synchronize(payload)

                # Sanitize and complete the packet for the ground station.
                payload["to"] = self._get_location()
                payload["rssi"] = None
                payload.pop("from_id")
                payload.pop("timestamp")
                self._data.append(payload)

                # Request the RSSI value for the received packet.
                self._sensor.send("at", command="DB")
            elif packet["id"] == "at_response":
                if packet["command"] == "DB":
                    # RSSI value has been received. Update the last received packet.
                    self._data[-1]["rssi"] = ord(packet["parameter"])
                elif packet["command"] == "SH":
                    # Serial number (high) has been received.
                    if self._address == None:
                        self._address = packet["parameter"]
                    else:
                        self._address = packet["parameter"] + self._address
                elif packet["command"] == "SL":
                    # Serial number (low) has been received.
                    if self._address == None:
                        self._address = packet["parameter"]
                    else:
                        self._address = self._address + packet["parameter"]
        else:
            payload = json.loads(packet["rf_data"])
            print("> Ground station received {}".format(payload))

    def _get_location(self):
        """
        Get the current GPS location (latitude and longitude pair) of the sensor.
        """

        return (random.uniform(1.0, 50.0), random.uniform(1.0, 50.0))