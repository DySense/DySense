# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

import numpy as np
import numpy.testing as np_test

from dysense.processing.platform_state import *

class TestRotatePlatformVectorToWorldFrame(unittest.TestCase):

    def test_positive_vector_with_positive_pitch(self):
        
        platform_vector = np.array([1, 0, 4])
        
        platform_orientation_deg = [0, 10, 0]

        world_vector = rotate_platform_vector_to_world_frame(platform_vector, platform_orientation_deg)

        # Expect forward direction to increase and be in north (X) direction since no yaw.
        # And downward in world frame to decrease, easting should be zero because no roll.
        self.assertTrue(world_vector[0] > platform_vector[0])
        self.assertTrue(world_vector[1] == 0)
        self.assertTrue(world_vector[2] < platform_vector[2])
        
    def test_positive_vector_with_negative_roll(self):
        
        platform_vector = np.array([0, 1, 4])
        
        platform_orientation_deg = [-10, 0, 0]

        world_vector = rotate_platform_vector_to_world_frame(platform_vector, platform_orientation_deg)

        # Expect 'right' direction to increase and be in east (Y) direction since no yaw.
        # And downward in world frame to decrease, northing should be zero because no pitch.
        self.assertTrue(world_vector[0] == 0)
        self.assertTrue(world_vector[1] > platform_vector[1])
        self.assertTrue(world_vector[2] < platform_vector[2])

if __name__ == '__main__':
    
    unittest.main()