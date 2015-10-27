import unittest
import socket
import time
import random
import copy
from mock import patch
from ..settings import Arguments
from ..zigbee.XBee_Packet import XBee_Packet
from ..zigbee.XBee_TDMA_Scheduler import XBee_TDMA_Scheduler
from ..zigbee.XBee_Viewer import XBee_Viewer
from ..zigbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator

class TestXBeeSensorSimulator(unittest.TestCase):
    def get_location(self):
        """
        Get the current GPS location (latitude and longitude pair).
        """

        return (random.uniform(1.0, 50.0), random.uniform(1.0, 50.0))

    @patch("matplotlib.pyplot.show")
    def setUp(self, mock_show):
        self.id = 1
        self.arguments = Arguments("settings.json", [])
        self.settings = self.arguments.get_settings("xbee_sensor_simulator")
        self.scheduler = XBee_TDMA_Scheduler(self.id, self.arguments)
        self.viewer = XBee_Viewer(self.arguments)
        self.sensor = XBee_Sensor_Simulator(self.id, self.arguments,
                                            self.scheduler, self.viewer,
                                            self.get_location)

        self.viewer.draw_points()

    def test_initialization(self):
        # The ID of the sensor must be set.
        self.assertEqual(self.sensor.id, self.id)

        # The next timestamp must be set.
        self.assertNotEqual(self.sensor._next_timestamp, 0)

        # The sweep data list must be empty.
        self.assertEqual(self.sensor._data, [])

    def test_send(self):
        # After sending, the sweep data list must be reset.
        self.sensor._send()
        self.assertEqual(self.sensor._data, [])

    def test_receive(self):
        # Create a packet from sensor 2 to the current sensor.
        packet = XBee_Packet()
        packet.set("_from_id", 2)
        packet.set("_timestamp", time.time())
        
        # After receiving that packet, the next timestamp must be synchronized.
        # Note that we must make a copy as the receive method will change the packet!
        copied_packet = copy.deepcopy(packet)
        self.sensor._receive(packet)
        self.assertEqual(self.sensor._next_timestamp,
                         self.scheduler.synchronize(copied_packet))

    def test_deactivate(self):
        # After deactivation the socket should be closed.
        self.sensor.deactivate()
        with self.assertRaises(socket.error):
            self.sensor._socket.sendto("foo", ("127.0.0.1", 100))
