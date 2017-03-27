# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

import numpy as np
import numpy.testing as np_test

from dysense.core.utility import *

class TestInterpolateAngleFromSet(unittest.TestCase):

    def setUp(self):

        self.x_set = range(5)
        self.angles = [0, 170, -170, 0, 90]

    def test_in_range_value(self):

        x_value = 1.75
        angle = interp_angle_deg_from_set(x_value, self.x_set, self.angles)
        self.assertAlmostEqual(angle, -175)

    def test_exact_value(self):

        x_value = 2
        angle = interp_angle_deg_from_set(x_value, self.x_set, self.angles)
        self.assertAlmostEqual(angle, -170)

    def test_before_range_value(self):

        x_value = -2
        angle = interp_angle_deg_from_set(x_value, self.x_set, self.angles, max_x_diff=1)
        self.assertTrue(math.isnan(angle))

    def test_after_range_value(self):

        x_value = 12
        angle = interp_angle_deg_from_set(x_value, self.x_set, self.angles, max_x_diff=1)
        self.assertTrue(math.isnan(angle))

class TestInterpolateSingleFromSet(unittest.TestCase):

    def setUp(self):

        self.x_set = range(10)
        self.y_set = [2*x for x in self.x_set]

    def test_in_range_value(self):

        x_value = 2.926
        y_value = interp_single_from_set(x_value, self.x_set, self.y_set)
        self.assertAlmostEqual(y_value, x_value * 2)

    def test_exact_value(self):

        x_value = 2
        y_value = interp_single_from_set(x_value, self.x_set, self.y_set)
        self.assertAlmostEqual(y_value, x_value * 2)

    def test_before_range_value(self):

        x_value = -2
        y_value = interp_single_from_set(x_value, self.x_set, self.y_set, max_x_diff=1)
        self.assertTrue(math.isnan(y_value))

    def test_after_range_value(self):

        x_value = 12
        y_value = interp_single_from_set(x_value, self.x_set, self.y_set, max_x_diff=1)
        self.assertTrue(math.isnan(y_value))

class TestInterpolateListFromSet(unittest.TestCase):

    def setUp(self):

        self.x_set = range(10)
        self.y_set = [(x, x+1) for x in self.x_set]

    def test_in_range_value(self):

        x_value = 2.926
        y_value = interp_list_from_set(x_value, self.x_set, self.y_set)
        self.assertAlmostEqual(y_value[0], x_value)
        self.assertAlmostEqual(y_value[1], x_value+1)

    def test_exact_value(self):

        x_value = 2
        y_value = interp_list_from_set(x_value, self.x_set, self.y_set)
        self.assertAlmostEqual(y_value[0], x_value)
        self.assertAlmostEqual(y_value[1], x_value+1)

    def test_before_range_value(self):

        x_value = -2
        y_value = interp_list_from_set(x_value, self.x_set, self.y_set, max_x_diff=1)
        self.assertTrue(math.isnan(y_value[0]))
        self.assertTrue(math.isnan(y_value[1]))

    def test_after_range_value(self):

        x_value = 12
        y_value = interp_list_from_set(x_value, self.x_set, self.y_set, max_x_diff=1)
        self.assertTrue(math.isnan(y_value[0]))
        self.assertTrue(math.isnan(y_value[1]))

class TestInterpolateAngle(unittest.TestCase):

    def test_increasing_wrap_pi(self):

        actual_angle = interp_angle_deg(170, -170, .5)
        self.assertAlmostEqual(actual_angle, 180)

    def test_decreasing_wrap_pi(self):

        actual_angle = interp_angle_deg(-170, 170, .5)
        self.assertAlmostEqual(actual_angle, -180)

    def test_positive_wrap_zero(self):

        actual_angle = interp_angle_deg(90, -90, .5)
        self.assertAlmostEqual(actual_angle, 0)

    def test_negative_wrap_pi(self):

        actual_angle = interp_angle_deg(-90, 90, .5)
        self.assertAlmostEqual(actual_angle, -180.0)

    def test_positive_increasing(self):

        actual_angle = interp_angle_deg(45, 55, .25)
        self.assertAlmostEqual(actual_angle, 47.5)

    def test_positive_decreasing(self):

        actual_angle = interp_angle_deg(55, 45, .25)
        self.assertAlmostEqual(actual_angle, 52.5)

    def test_negative_increasing(self):

        actual_angle = interp_angle_deg(-55, -45, .25)
        self.assertAlmostEqual(actual_angle, -52.5)

    def test_negative_decreasing(self):

        actual_angle = interp_angle_deg(-45, -55, .25)
        self.assertAlmostEqual(actual_angle, -47.5)

    def test_positive_diff_180(self):

        actual_angle = interp_angle_deg(90, -90, .25)
        self.assertAlmostEqual(actual_angle, 45)

    def test_negative_wrap_45(self):

        actual_angle = interp_angle_deg(90, -90, .25)
        self.assertAlmostEqual(actual_angle, 45)

if __name__ == '__main__':

    unittest.main()