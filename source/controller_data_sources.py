
class AbstractDataSource(object):
    
    def __init__(self, callback, controller_id='none', sensor_id='-1', sensor_metadata=None):
        
        self.callback = callback
        
        self.update(controller_id, sensor_id, sensor_metadata, notify_callback=False)
        
    @property
    def public_info(self):
        return { 'controller_id': self.controller_id,
                 'sensor_id': self.sensor_id,
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
    @property
    def sensor_metadata(self):
        return self._sensor_metadata
    @property
    def sensor_output_names(self):
        return [outparam['name'] for outparam in self.sensor_metadata['data']]
        
    def update(self, controller_id, sensor_id, sensor_metadata, notify_callback=True):
        
        self._controller_id = controller_id
        self._sensor_id = sensor_id
        self._receiving = False
        self._sensor_metadata = sensor_metadata
        
        if sensor_metadata is not None:
            self.verify_metadata()

        if notify_callback:
            self.callback()
            
    def matches(self, sensor_id, controller_id):
        return (sensor_id == self.sensor_id) and (controller_id == self.controller_id)
        
    def verify_metadata(self):
        raise NotImplementedError
     
class TimeDataSource(AbstractDataSource):
    
    def __init__(self, **kargs):
        super(TimeDataSource, self).__init__(**kargs)
        self.utc_time_idx = -1
        self.sys_time_idx = -1
        
    def verify_metadata(self):
        try:
            self.utc_time_idx = self.sensor_output_names.index('utc_time')
            self.sys_time_idx = self.sensor_output_names.index('sys_time')
        except ValueError:
            raise ValueError("Could not find 'utc_time' and 'sys_time' in sensor output types {}".format(self.sensor_output_names))
        
class PositionDataSource(AbstractDataSource):
    
    def __init__(self, **kargs):
        super(PositionDataSource, self).__init__(**kargs)
        self.position_idx = -1
        
    def verify_metadata(self):
        try:
            self.position_idx = self.sensor_metadata['data'].index('position')
        except ValueError:
            raise ValueError("Could not find 'position' in sensor output types {}".format(self.sensor_metadata['data']))

class OrientationDataSource(AbstractDataSource):
    
    def __init__(self, **kargs):
        super(OrientationDataSource, self).__init__(**kargs)
        self.orientation_idx = -1
        
    def verify_metadata(self):
        try:
            self.orientation_idx = self.sensor_metadata['data'].index('orientation')
        except ValueError:
            raise ValueError("Could not find 'orientation' in sensor output types {}".format(self.sensor_metadata['data']))