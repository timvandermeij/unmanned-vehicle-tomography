__all__ = [
    "SVD_Reconstructor", "Total_Variation_Reconstructor", "Truncated_SVD_Reconstructor"
]

class Reconstructor(object):
    def __init__(self, settings):
        """
        Initialize the reconstructor object.
        """

        self._settings = settings

    def execute(self, weight_matrix, rssi, buffer=None, guess=None):
        raise NotImplementedError("Subclasses must implement execute(weight_matrix, rssi, buffer, guess)")
