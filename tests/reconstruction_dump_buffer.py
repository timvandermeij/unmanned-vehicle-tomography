import unittest
from ..reconstruction.Dump_Buffer import Dump_Buffer

class TestReconstructionDumpBuffer(unittest.TestCase):
    def test_initialization(self):
        # Dump buffers are regular buffers with the exception that they
        # populate the queue with XBee packets read from a JSON data file.
        # Verify that these are set correctly upon initialization.
        options = {
            "calibration_file": "tests/reconstruction/dump_empty.json",
            "file": "tests/reconstruction/dump.json"
        }
        dump_buffer = Dump_Buffer(options)

        self.assertEqual(dump_buffer.number_of_sensors, 2)
        self.assertEqual(dump_buffer.origin, [0, 0])
        self.assertEqual(dump_buffer.size, [10, 10])

        self.assertEqual(dump_buffer.count(), 2)

        # The calibration RSSI value for the link must be subtracted
        # from the originally measured RSSI value.
        first_packet, first_calibrated_rssi = dump_buffer.get()
        self.assertEqual(first_packet.get_all(), {
            "specification": "rssi_ground_station",
            "sensor_id": 1,
            "from_latitude": 1,
            "from_longitude": 0,
            "from_valid": True,
            "to_latitude": 1,
            "to_longitude": 10,
            "to_valid": True,
            "rssi": -38
        })
        self.assertEqual(first_calibrated_rssi, -38 - -36)

        second_packet, second_calibrated_rssi = dump_buffer.get()
        self.assertEqual(second_packet.get_all(), {
            "specification": "rssi_ground_station",
            "sensor_id": 2,
            "from_latitude": 0,
            "from_longitude": 2,
            "from_valid": True,
            "to_latitude": 6,
            "to_longitude": 10,
            "to_valid": True,
            "rssi": -41
        })
        self.assertEqual(second_calibrated_rssi, -41 - -38)

        self.assertEqual(dump_buffer.get(), None)
        self.assertEqual(dump_buffer.count(), 0)
