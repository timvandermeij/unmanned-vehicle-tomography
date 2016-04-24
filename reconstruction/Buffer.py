import Queue
from ..zigbee.XBee_Packet import XBee_Packet

class Buffer(object):
    def __init__(self, options=None):
        """
        Initialize the buffer object.
        """

        if options is None:
            raise ValueError("Options for the buffer have not been provided.")

        self._number_of_sensors = 0
        self._origin = [0, 0]
        self._size = [0, 0]

        self._queue = Queue.Queue()
        self._calibration = {}

    def get(self):
        """
        Get a packet from the buffer (or None if the queue is empty).
        """

        if self._queue.empty():
            return None

        return self._queue.get()

    def put(self, packet):
        """
        Put a packet into the buffer.
        """

        if not isinstance(packet, XBee_Packet):
            raise ValueError("The provided packet is not an XBee packet.")

        self._queue.put(packet)

    def count(self):
        """
        Count the number of packets in the buffer.
        """

        return self._queue.qsize()

    @property
    def number_of_sensors(self):
        """
        Return the number of sensors in the network.
        """

        return self._number_of_sensors

    @property
    def origin(self):
        """
        Return the origin of the network.
        """

        return self._origin

    @property
    def size(self):
        """
        Return the size of the network.
        """

        return self._size
