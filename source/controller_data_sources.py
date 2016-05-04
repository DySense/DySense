# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time

class AbstractDataSource(object):
    
    def __init__(self, callback, **kargs):
        
        self.callback = callback
        self._controller_id = kargs.get('controller_id', 'None')
        self._sensor_id = kargs.get('sensor_id', 'None')
        self._sensor_metadata = kargs.get('metadata', None)
        
        # The minimum amount of time that needs to elapse without being updated before
        # the sensor is considered as 'not receiving'.
        self.timeout_duration = 1.5
        
        # The last time the source received new data.
        self.last_update_time = 0
        
        if self.sensor_metadata is not None:
            self.verify_metadata()

    @property
    def public_info(self):
        return { 'controller_id': self.controller_id,
                 'sensor_id': self.sensor_id,
                 'metadata': self.sensor_metadata,
                 'receiving': self.receiving }
        
    @property
    def controller_id(self):
        return self._controller_id
    @property
    def sensor_id(self):
        return self._sensor_id
    @property
    def receiving(self):
        if self.sensor_id in ['derived', 'none']:
            return True # always report as receiving because will never get data
        else:
            return time.time() <= (self.last_update_time + self.timeout_duration)
    @property
    def sensor_metadata(self):
        return self._sensor_metadata
    @property
    def sensor_output_names(self):
        return [outparam['name'] for outparam in self.sensor_metadata['data']]
    
    def mark_updated(self):
        self.last_update_time = time.time()
    
    def get_matching_tag_idx(self, desired_tag_name):
        for i, data in enumerate(self.sensor_metadata['data']):
            if desired_tag_name in data.get('tags',[]):
                return i
        raise ValueError
            
    def matches(self, sensor_id, controller_id):
        return (sensor_id == self.sensor_id) and (controller_id == self.controller_id)
        
    def verify_metadata(self):
        raise NotImplementedError
     
class TimeDataSource(AbstractDataSource):
    
    def __init__(self, callback,  **kargs):
        super(TimeDataSource, self).__init__(callback, **kargs)
        
    def verify_metadata(self):
        # UTC and system time are standardized as the first and second piece of data passed so don't need to lookup indices.
        pass
        
class PositionDataSource(AbstractDataSource):
    
    def __init__(self, callback, **kargs):
        self.position_x_idx = None
        self.position_y_idx = None
        self.position_z_idx = None
        self.position_zone_idx = None
        super(PositionDataSource, self).__init__(callback, **kargs)
        
    def verify_metadata(self):

        try:
            self.position_x_idx = self.get_matching_tag_idx('position_x')
            self.position_y_idx = self.get_matching_tag_idx('position_y')
            self.position_z_idx = self.get_matching_tag_idx('position_z')
        except ValueError:
            raise ValueError("Could not find valid x, y and z position tags in sensor metadata")

        # Zone is optional so don't raise exception if not found
        try:
            self.position_zone_idx = self.get_matching_tag_idx('position_zone')
        except ValueError:
            self.position_zone_idx = None

class OrientationDataSource(AbstractDataSource):
    
    def __init__(self, callback, angle_name, **kargs):
        self.orientation_idx = None
        self.angle_name = angle_name
        super(OrientationDataSource, self).__init__(callback, **kargs)
        
    def verify_metadata(self):

        try:
            self.orientation_idx = self.get_matching_tag_idx(self.angle_name)
        except ValueError:
            raise ValueError("Could not find {} tag in sensor metadata".format(self.angle_name))