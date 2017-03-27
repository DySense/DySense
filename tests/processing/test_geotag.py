# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

import math
import numpy as np
import numpy.testing as np_test

from dysense.processing.geotagger import GeoTagger
from dysense.processing.utility import ObjectState

nan = float('NaN')

class TestGeotagger(unittest.TestCase):

    def setUp(self):

        self.geotagger = GeoTagger(max_time_diff=1)

    def test_no_platform_orientation(self):

        platform = ObjectState(utc_time=100, lat=39, long=-97, alt=1, roll=nan, pitch=nan, yaw=nan, height_above_ground=2.5)
        position_offsets = [1, 1, 1] # meters
        orientation_offsets_rad = [0, 0, 0] # radians

        reading = {'time': 100, 'data': [1, 2]}

        self.geotagger.tag_all_readings([reading], position_offsets, orientation_offsets_rad, [platform])

        reading_state = reading['state']

        # Should still be able to account for 'down' offset even if no orientation (assuming roll and pitch are zero)
        expected_reading_alt = platform.alt - position_offsets[2]
        expected_reading_height = platform.height_above_ground - position_offsets[2]

        # Sensor should have same lat/long since offsets can't be applied if no yaw.
        self.assertEqual(reading_state.lat, platform.lat)
        self.assertEqual(reading_state.long, platform.long)
        self.assertEqual(reading_state.alt, expected_reading_alt)
        self.assertEqual(reading_state.height_above_ground, expected_reading_height)

        # Sensor shouldn't have orientation because platform didn't.
        self.assertTrue(math.isnan(reading_state.roll))
        self.assertTrue(math.isnan(reading_state.pitch))
        self.assertTrue(math.isnan(reading_state.yaw))

    def test_zero_position_offsets(self):

        platform = ObjectState(utc_time=100, lat=39, long=-97, alt=1, roll=45, pitch=45, yaw=45, height_above_ground=2.5)
        position_offsets = [0, 0, 0] # meters
        orientation_offsets = [0, 0, 0] # radians

        reading = {'time': 100, 'data': [1, 2]}

        self.geotagger.tag_all_readings([reading], position_offsets, orientation_offsets, [platform])

        reading_state = reading['state']

        # Sensor should have same position and height so it has zero offsets.
        self.assertEqual(reading_state.lat, platform.lat)
        self.assertEqual(reading_state.long, platform.long)
        self.assertEqual(reading_state.alt, platform.alt)
        self.assertEqual(reading_state.height_above_ground, platform.height_above_ground)

    def test_orientation_offsets_with_zero_platform_orientation(self):

        platform = ObjectState(utc_time=100, lat=39, long=-97, alt=1, roll=0, pitch=0, yaw=0, height_above_ground=2.5)
        position_offsets = [0, 0, 0]
        orientation_offsets = [45, 5, 90]

        orientation_offsets_rad = [math.radians(angle) for angle in orientation_offsets]

        reading = {'time': 100, 'data': [1, 2]}

        self.geotagger.tag_all_readings([reading], position_offsets, orientation_offsets_rad, [platform])

        reading_state = reading['state']

        # Since platform orientation is (0,0,0) then offsets in the platform frame are the roll, pitch yaw in the world frame.
        self.assertEqual(list(reading_state.orientation), orientation_offsets)

    def test_orientation_offsets_with_nonzero_platform_yaw(self):

        platform = ObjectState(utc_time=100, lat=39, long=-97, alt=1, roll=25, pitch=0, yaw=90, height_above_ground=2.5)
        position_offsets = [0, 0, 0]
        orientation_offsets = [45, 5, 90]

        orientation_offsets_rad = [math.radians(angle) for angle in orientation_offsets]

        reading = {'time': 100, 'data': [1, 2]}

        self.geotagger.tag_all_readings([reading], position_offsets, orientation_offsets_rad, [platform])

        reading_state = reading['state']

        # Since sensor of offset 90 deg. from platform, then platform roll/pitch will affect with sensor (-pitch)/roll.
        expected_roll = orientation_offsets[0] + platform.pitch
        expected_pitch = orientation_offsets[1] - platform.roll
        expected_yaw = platform.yaw + orientation_offsets[2]

        expected_reading_orientation = (expected_roll, expected_pitch, expected_yaw)

        np_test.assert_almost_equal(np.array(reading_state.orientation), np.array(expected_reading_orientation))

    def test_gimbal_lock(self):

        platform = ObjectState(utc_time=100, lat=39, long=-97, alt=1, roll=0, pitch=45, yaw=90, height_above_ground=2.5)
        position_offsets = [0, 0, 0]
        orientation_offsets = [0, 45, 0]

        orientation_offsets_rad = [math.radians(angle) for angle in orientation_offsets]

        reading = {'time': 100, 'data': [1, 2]}

        self.geotagger.tag_all_readings([reading], position_offsets, orientation_offsets_rad, [platform])

        reading_state = reading['state']

        # Since at positive gimbal lock, yaw will show up as roll.
        expected_roll = -platform.yaw
        expected_pitch = platform.pitch + orientation_offsets[1]
        expected_yaw = 0

        expected_reading_orientation = (expected_roll, expected_pitch, expected_yaw)

        np_test.assert_almost_equal(np.array(reading_state.orientation), np.array(expected_reading_orientation))

if __name__ == '__main__':

    unittest.main()