# Core imports
import unittest

# Library imports
import numpy as np

# Package imports
from ..reconstruction.Ellipse_Model import Ellipse_Model
from ..settings.Arguments import Arguments

class TestReconstructionEllipseModel(unittest.TestCase):
    def setUp(self):
        super(TestReconstructionEllipseModel, self).setUp()

        self.arguments = Arguments("settings.json", [])
        self.settings = self.arguments.get_settings("reconstruction_ellipse_model")

        self.model = Ellipse_Model(self.arguments)

    def test_initialization(self):
        # The lambda member variable must be set.
        self.assertEqual(self.model._lambda, self.settings.get("lambda"))

    def test_type(self):
        # The `type` property must be implemented and correct.
        self.assertEqual(self.model.type, "reconstruction_ellipse_model")

    def test_assign(self):
        def distance(x, y):
            # Helper function to calculate the distance from location
            # (0, 0) to the pixel center location of pixel (x, y).
            return np.sqrt((x + 0.5) ** 2 + (y + 0.5) ** 2)

        # The grid contains 16 pixels (four by four). The link goes from
        # location (0, 0) to location (4, 4). Location (0, 0) is located
        # in the top left corner and location (4, 4) is located in the
        # bottom right corner of the grid.
        length = np.sqrt(4 ** 2 + 4 ** 2)
        source_distances = np.array([
            distance(0, 0), distance(1, 0), distance(2, 0), distance(3, 0),
            distance(0, 1), distance(1, 1), distance(2, 1), distance(3, 1),
            distance(0, 2), distance(1, 2), distance(2, 2), distance(3, 2),
            distance(0, 3), distance(1, 3), distance(2, 3), distance(3, 3)
        ]).reshape(4, 4)
        destination_distances = np.flipud(np.fliplr(source_distances))

        # The assigned weights must form an ellipse.
        weights = self.model.assign(length, source_distances, destination_distances)

        factor = 1.0 / np.sqrt(length)
        expected = np.array([
            # pylint: disable=bad-whitespace
            factor, factor, 0,      0,
            factor, factor, factor, 0,
            0,      factor, factor, factor,
            0,      0,      factor, factor
        ]).reshape(4, 4)

        self.assertTrue((weights == expected).all())
