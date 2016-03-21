import socket
import time
import random
import copy
import Queue
from core_thread_manager import ThreadableTestCase
from mock import patch, MagicMock
from ..core.Thread_Manager import Thread_Manager
from ..zigbee.XBee_Packet import XBee_Packet
from ..zigbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator
from ..settings import Arguments
from settings import SettingsTestCase

class TestXBeeSensorSimulator(ThreadableTestCase, SettingsTestCase):
    def location_callback(self):
        """
        Get the current GPS location (latitude and longitude pair).
        """

        return (random.uniform(1.0, 50.0), random.uniform(1.0, 50.0))

    def receive_callback(self, packet):
        pass

    def valid_callback(self, other_valid=None):
        return True

    def setUp(self):
        # We need to mock the Matplotlib module as we do not want to use
        # plotting facilities during the tests.
        self.matplotlib_mock = MagicMock()
        modules = {
            'matplotlib': self.matplotlib_mock,
            'matplotlib.pyplot': self.matplotlib_mock.pyplot
        }

        self.patcher = patch.dict('sys.modules', modules)
        self.patcher.start()

        self.sensor_id = 1
        self.arguments = Arguments("settings.json", [
            "--warnings", "--xbee-id", "1"
        ])
        self.settings = self.arguments.get_settings("xbee_sensor_simulator")
        self.thread_manager = Thread_Manager()
        self.sensor = XBee_Sensor_Simulator(self.arguments,
                                            self.thread_manager,
                                            None,
                                            self.location_callback,
                                            self.receive_callback,
                                            self.valid_callback)
        self.sensor.setup()
        self.sensor._active = True

    def test_initialization(self):
        # The ID of the sensor must be set.
        self.assertEqual(self.sensor._id, self.sensor_id)

        # The next timestamp must be zero.
        self.assertEqual(self.sensor._next_timestamp, 0)

        # The location, receive and valid callbacks must be set.
        self.assertTrue(hasattr(self.sensor._location_callback, "__call__"))
        self.assertTrue(hasattr(self.sensor._receive_callback, "__call__"))
        self.assertTrue(hasattr(self.sensor._valid_callback, "__call__"))

        # The sweep data list must be empty.
        self.assertEqual(self.sensor._data, [])

        # The custom packet queue must be empty.
        self.assertIsInstance(self.sensor._queue, Queue.Queue)
        self.assertEqual(self.sensor._queue.qsize(), 0)

    def test_get_identity(self):
        # The identity of the device must be returned as a dictionary.
        identity = self.sensor.get_identity()
        self.assertIsInstance(identity, dict)
        self.assertEqual(identity["id"], self.sensor_id)
        self.assertEqual(identity["address"], "{}:{}".format(self.sensor._ip, self.sensor._port))
        self.assertEqual(identity["joined"], True)

    def test_enqueue(self):
        # Packets that are not XBee_Packet objects should be refused.
        with self.assertRaises(TypeError):
            packet = {
                "foo": "bar"
            }
            self.sensor.enqueue(packet)

        # Private packets should be refused.
        with self.assertRaises(ValueError):
            packet = XBee_Packet()
            packet.set("specification", "rssi_broadcast")
            self.sensor.enqueue(packet)

        # Packets that do not contain a destination should be broadcasted.
        # We subtract one because we do not send to ourself.
        packet = XBee_Packet()
        packet.set("specification", "memory_map_chunk")
        packet.set("latitude", 123456789.12)
        packet.set("longitude", 123459678.34)
        self.sensor.enqueue(packet)
        self.assertEqual(self.sensor._queue.qsize(),
                         self.settings.get("number_of_sensors") - 1)
        self.sensor._queue = Queue.Queue()

        # Valid packets should be enqueued.
        packet = XBee_Packet()
        packet.set("specification", "memory_map_chunk")
        packet.set("latitude", 123456789.12)
        packet.set("longitude", 123459678.34)
        self.sensor.enqueue(packet, to=2)
        self.assertEqual(self.sensor._queue.get(), {
            "packet": packet,
            "to": 2
        })

    def test_send(self):
        # After sending, the sweep data list must be empty.
        self.sensor._send()
        self.assertEqual(self.sensor._data, [])

    def test_send_custom_packets(self):
        # If the queue contains packets, some of them must be sent.
        packet = XBee_Packet()
        packet.set("specification", "memory_map_chunk")
        packet.set("latitude", 123456789.12)
        packet.set("longitude", 123459678.34)
        self.sensor.enqueue(packet, to=2)

        queue_length_before = self.sensor._queue.qsize()
        self.sensor._send_custom_packets()
        custom_packet_limit = self.settings.get("custom_packet_limit")
        queue_length_after = max(0, queue_length_before - custom_packet_limit)
        self.assertEqual(self.sensor._queue.qsize(), queue_length_after)

    def test_receive(self):
        # Create a packet from sensor 2 to the current sensor.
        packet = XBee_Packet()
        packet.set("specification", "rssi_broadcast")
        packet.set("latitude", 123456789.12)
        packet.set("longitude", 123459678.34)
        packet.set("valid", True)
        packet.set("sensor_id", 2)
        packet.set("timestamp", time.time())

        # After receiving that packet, the next timestamp must be synchronized.
        # Note that we must make a copy as the receive method will change the packet!
        copied_packet = copy.deepcopy(packet)
        self.sensor._receive(packet)
        self.assertEqual(self.sensor._next_timestamp,
                         self.sensor._scheduler.synchronize(copied_packet))

    def test_deactivate(self):
        # After deactivation the socket should be closed.
        self.sensor.deactivate()
        with self.assertRaises(socket.error):
            self.sensor._socket.sendto("foo", ("127.0.0.1", 100))
