
class AbstractDataSource(object):
    
    def __init__(self, callback, **kargs):
        
        self.callback = callback
        self._controller_id = kargs.get('controller_id', 'None')
        self._sensor_id = kargs.get('sensor_id', 'None')
        self._receiving = False
        self._sensor_metadata = kargs.get('metadata', None)
        
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
        return self._receiving
    @receiving.setter
    def receiving(self, new_value):
        self._receiving = new_value
        self.callback()
    @property
    def sensor_metadata(self):
        return self._sensor_metadata
    @property
    def sensor_output_names(self):
        return [outparam['name'] for outparam in self.sensor_metadata['data']]
    
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
        self.utc_time_idx = None
        self.sys_time_idx = None
        super(TimeDataSource, self).__init__(callback, **kargs)
        
    def verify_metadata(self):
        try:
            self.utc_time_idx = self.sensor_output_names.index('utc_time')
            self.sys_time_idx = self.sensor_output_names.index('sys_time')
        except ValueError:
            raise ValueError("Could not find 'utc_time' and 'sys_time' in sensor output types {}".format(self.sensor_output_names))
        
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