# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from dysense.core.utility import element_index

class Database(object):
    '''TODO'''
    
    def __init__(self, log):
        '''Constructor'''
        
        # The log is from the standard python logging module. Use it (+ set the command line arguments) instead of print statements.
        self.log = log
    
        # Lookup tables that I reference in the comments / examples below
        # feel free to rename or edit these since I can't remember exactly how you structured the tables
        # I added a test_sensor_python since that's in the example data I sent you.  You could make a table just for testing.
        # note 'counter' is a string, not an integer.
        self.sensor_type_to_table_name = {'canon_edsdk': 'images_table',
                                          'test_sensor_python': 'test_table',
                                         }

        # The values are data names (defined in sensor_metadata.yaml) listed in the order they appear in the database table.
        # The names don't have to match the database fields exactly, just the ordering matters.
        self.sensor_type_to_table_elements = {'canon_edsdk': ['image_name'],
                                              'test_sensor_python': ['counter', 'rand_int', 'rand_float'],
                                             }
    
    def upload(self, session):
        '''TODO'''
        
        # Angles are in degrees.
        # Distances like altitude, height above ground are in meters.
        # Altitude are above WGS-84 ellipsoid.
        
        # Strings are stored as unicode, but should be decoded into UTF8 format before loading into table.
        # See: http://stackoverflow.com/questions/3328968/how-to-store-unicode-in-mysql
        # If for some reason that doesn't work and/or the python library you use doesn't accept unicode
        # then use the make_utf8() function in dysense/core/utility.py
        
        # If information isn't available (i.e. it's optional) then it's stored as NaN
        # i.e. float('NaN') you can check this using math.isnan().  I think storing it as 0 would be misleading.
        # The only information that should be 'optional' are
        #   - roll angles, pitch angles, yaw angles (not the offsets, but the actual angles)
        #   - height above ground
        # These are all in ObjectState (see processing/utility.py)
        # If the rest of the program is correct you shouldn't receive any ObjectState's that have lat/long/alt as NaN 
        # but if you want to be safe and check before inserting into DB then that's probably a good idea.
        
        # Another thing is that all angles in ObjectState should be between +/- 180 degrees (if not NaN).
        # Again this should already be true but you can add in checks for it.
        
        # It would be best to set a breakpoint and inspect 'session', but some examples are below.
        
        # This dictionary stores all the metadata about the session.
        # See 'session_info.csv' file in session directory for the name of keys.
        session_info = session['session_info']
        
        # Sensors store geotagged log data + metadata about sensor.
        for sensor in session['sensors']:
            
            # All this "sensor metadata" comes from the files in the "sensor_info/" directory.
            
            # This is the 'type' of the sensor which maps 1-1 with the sensors stored in 'dysense/metadata/sensor_metadata.yaml'
            # For example 'canon_edsdk' for the Canon cameras. 
            # If you look in this file I think we should have a lookup table (in this Database class) that maps these 'sensor_types' to a
            # certain table.
            sensor['sensor_type']

            # Same thing as serial number
            sensor['instrument_tag']
            
            # Prefix to serial number.  Instrument ID = Instrument Type + '-' + Instrument Tag
            # This is essentially the 'class' of the sensor (e.g. GNSS or IRT or USC)
            sensor['instrument_type']
        
            # Note use 'adjusted_position_offets' instead of 'position_offets'.
            # All offsets are always finite values.
            sensor['adjusted_position_offsets']
            sensor['orientation_offsets']
        
            # The metadata keys stores all the info for this sensor from the 'dysense/metadata/sensor_metadata.yaml' file.
            # The only key you should need is 'data' (i.e. sensor['metadata']['data']) which describes the output data of a sensor.
            # This is useful because some sensors might output data that we don't necessarily want to upload
            # to the database.  
            # I added an example below of what I mean by this and using the log data.
            sensor['log_data']
                
            # Everything else below you might not need for uploading to the database...
            # but might be useful when logging warning or error messages.

            # The human-readable name of the sensor (e.g. irt-1). 
            # Sorry the name is confusing, it really should be 'sensor-name'
            sensor['sensor_id']
            
            # Essentially the name of the computer that the sensor was used on.            
            sensor['controller_id']
            
            # These are messages that were sent by the sensor driver when it was running.
            # You shouldn't need to do anything with these.
            sensor['text_messages']
            
            # Name of original log file (not including position/orientation info)
            sensor['log_file_name']
            
            # Values of user specified settings (e.g. COM port, baud rate, etc)
            sensor['settings']
                
        for platform_state in session['platform_states']:
            # These are ObjectState elements (see bottom of utilty.py)
            # Should be able to load platform_state table from these elements.
            # These are already filtered down before this method as specified by the user.  So 
            # if recorded at 50Hz might only be listed 5Hz or something.
            pass
        
        # Example of uploading data to table
        for sensor in session['sensors']:
            
            sensor_type = sensor['sensor_type']
            
            try:
                table_name = self.sensor_type_to_table_name[sensor_type]
            except KeyError:
                self.log.error('No table listed for sensor type {}'.format(sensor_type))
                continue
        
            # Get list of data_indices for the pieces of data that we should upload to database. 
            table_elements = self.sensor_type_to_table_elements[sensor_type]
            sensor_data_names = [d['name'] for d in sensor['metadata']['data']]
            data_indices = [element_index(e, sensor_data_names) for e in table_elements]
        
            for reading in sensor['log_data']:
                
                # UTC time of the reading stored as seconds since epoch
                reading['time']

                # List of values that we should upload to database in the correct ordering.
                all_reading_values = reading['data']
                reading_values = [all_reading_values[i] for i in data_indices]
                
                # ObjectState of sensor at time of reading (see bottom of utility.py)
                reading['state']
        
                # TODO actually insert row into table
        
        return True # successful upload
