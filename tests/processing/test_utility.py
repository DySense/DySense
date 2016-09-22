# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

import numpy as np
import numpy.testing as np_test

from dysense.processing.utility import *

class TestRPYFromRotationMatrix(unittest.TestCase):

    def test_arbitrary_rpy(self):
        
        roll = math.pi/5
        pitch = -math.pi/10
        yaw = math.pi/4
        rot_matrix = rot_parent_to_child(roll, pitch, yaw)
        returned_roll, returned_pitch, returned_yaw = rpy_from_rot_matrix(rot_matrix)
        self.assertAlmostEqual(roll, returned_roll, 10)
        self.assertAlmostEqual(pitch, returned_pitch, 10)
        self.assertAlmostEqual(yaw, returned_yaw, 10)
        
    def test_outside_bounds_rpy(self):
        # Test roll and yaw returned within +/- PI and pitch returned within +/- PI/2
        roll = math.radians(210)
        pitch = math.radians(135)
        yaw = math.radians(-190)
        rot_matrix = rot_parent_to_child(roll, pitch, yaw)
        returned_roll, returned_pitch, returned_yaw = rpy_from_rot_matrix(rot_matrix)
        expected_roll = math.radians(30)
        expected_pitch = math.radians(45)
        expected_yaw = math.radians(-10)
        self.assertAlmostEqual(expected_roll, returned_roll, 10)
        self.assertAlmostEqual(expected_pitch, returned_pitch, 10)
        self.assertAlmostEqual(expected_yaw, returned_yaw, 10)
        
    def test_positive_gimbal_lock(self):

        roll = math.radians(0)
        pitch = math.radians(90)
        yaw = math.radians(15)
        rot_matrix = rot_parent_to_child(roll, pitch, yaw)
        returned_roll, returned_pitch, returned_yaw = rpy_from_rot_matrix(rot_matrix)
        expected_roll = math.radians(-15)
        expected_pitch = math.radians(90)
        expected_yaw = math.radians(0)
        self.assertAlmostEqual(expected_roll, returned_roll, 10)
        self.assertAlmostEqual(expected_pitch, returned_pitch, 10)
        self.assertAlmostEqual(expected_yaw, returned_yaw, 10)
        
    def test_negative_gimbal_lock(self):

        roll = math.radians(0)
        pitch = math.radians(-90)
        yaw = math.radians(135)
        rot_matrix = rot_parent_to_child(roll, pitch, yaw)
        returned_roll, returned_pitch, returned_yaw = rpy_from_rot_matrix(rot_matrix)
        expected_roll = math.radians(135)
        expected_pitch = math.radians(-90)
        expected_yaw = math.radians(0)
        self.assertAlmostEqual(expected_roll, returned_roll, 10)
        self.assertAlmostEqual(expected_pitch, returned_pitch, 10)
        self.assertAlmostEqual(expected_yaw, returned_yaw, 10)

class TestRotateParentToChild(unittest.TestCase):

    def test_zero_rotation(self):
        
        np_test.assert_equal(rot_parent_to_child(0, 0, 0), np.identity(3))
        
    def test_pointing_straight_up(self):
        # Rotate positive X by 90, 90, 90 deg. and that should be the vector pointing
        # out the bottom of the child frame (positive z)
        rotation_matrix = rot_parent_to_child(math.pi/2, math.pi/2, math.pi/2)
        rotated_vec = np.dot(rotation_matrix, np.array([1, 0, 0]))
        np_test.assert_almost_equal(rotated_vec, np.array([0, 0, -1]))

    def test_pointing_straight_down(self):
        # Rotate positive X by 90, -90, 90 deg. and that should be the vector pointing
        # out the top of the child frame (negative z)
        rotation_matrix = rot_parent_to_child(math.pi/2, -math.pi/2, math.pi/2)
        rotated_vec = np.dot(rotation_matrix, np.array([1, 0, 0]))
        np_test.assert_almost_equal(rotated_vec, np.array([0, 0, 1]))
        
    def test_arbitrary_rotation(self):
        # Expected matrix taken from:
        # http://danceswithcode.net/engineeringnotes/rotations_in_3d/demo3D/rotations_in_3d_tool.html
        actual_matrix = rot_parent_to_child(math.radians(66), math.radians(50), math.radians(45))
        expected_matrix = np.array([[.4545, .2072, .8662],
                                    [.4545, .7824, -.4257],
                                    [-.7661, .5872, .2614]])
        np_test.assert_almost_equal(actual_matrix, expected_matrix, decimal=4)

class TestRotationAboutZ(unittest.TestCase):

    def test_zero_rotation(self):
        
        np_test.assert_equal(rot_z(0), np.identity(3))
        
    def test_positive_rotation(self):
        
        rotated_vec = np.dot(rot_z(math.pi/2), np.array([1, 1, 1]))
        np_test.assert_almost_equal(rotated_vec, np.array([-1, 1, 1]))

    def test_negative_rotation(self):
        
        rotated_vec = np.dot(rot_z(-math.pi/2), np.array([1, 1, 1]))
        np_test.assert_almost_equal(rotated_vec, np.array([1, -1, 1]))

class TestRotationAboutX(unittest.TestCase):

    def test_zero_rotation(self):
        
        np_test.assert_equal(rot_x(0), np.identity(3))
        
    def test_positive_rotation(self):
        
        rotated_vec = np.dot(rot_x(math.pi/2), np.array([1, 1, 1]))
        np_test.assert_almost_equal(rotated_vec, np.array([1, -1, 1]))

    def test_negative_rotation(self):
        
        rotated_vec = np.dot(rot_x(-math.pi/2), np.array([1, 1, 1]))
        np_test.assert_almost_equal(rotated_vec, np.array([1, 1, -1]))
    
class TestRotationAboutY(unittest.TestCase):
        
    def test_zero_rotation(self):
        
        np_test.assert_equal(rot_y(0), np.identity(3))
        
    def test_positive_rotation(self):
        
        rotated_vec = np.dot(rot_y(math.pi/2), np.array([1, 1, 1]))
        np_test.assert_almost_equal(rotated_vec, np.array([1, 1, -1]))

    def test_negative_rotation(self):
        
        rotated_vec = np.dot(rot_y(-math.pi/2), np.array([1, 1, 1]))
        np_test.assert_almost_equal(rotated_vec, np.array([-1, 1, 1]))

if __name__ == '__main__':
    
    unittest.main()