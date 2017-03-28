# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from dysense.core.utility import element_index
#from dysense.core import local_config
from dysense.core import config
from dysense.processing.log import log

import mysql.connector
from mysql.connector import errorcode

import datetime
import time
import math
import sys
import hashlib # Will be used to compute MD5 checksum of (image) files once the way to do this is determined

dateTimeFormat="%Y%m%d-%H%M%S"

# TO DO - March 27,2017
#   1. Determine whether initialization code to retrieve mapping of sensor type to table name can be automated by
#      including the table name for each sensor in the sensor_metadata.yaml file
#   2. Determine whether initialization code to retrieve mapping of sensor type to table elements
#      can be automated by reading the table elements for each sensor from the sensor_metadata.yaml file
#   3. Determine best place to compute MD5 checksum of images
#   4. Decide whether experiment_id is needed in run table and compute if required
#   5. Determine whether run_table columns region & country can be populated reliably using geotagging code.
#      Problem is that GoogleV3 geocoder returns data for different countries in different fields


def convert_NaN_to_None(value):

    # Convert NaN to None required for mysqlconnector API

    if math.isnan(value):
        checked_value = None
    else:
        checked_value = value
    return checked_value


def open_db_connection(config):

    # Connect to the HTP database
        try:
            cnx = mysql.connector.connect(user=config.USER, password=config.PASSWORD,
                                          host=config.HOST, port=config.PORT,
                                          database=config.DATABASE)
            log().info('Connecting to Database: ' + cnx.database)

        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                log().error("Something is wrong with your user name or password")
                sys.exit()
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                log().error("Database does not exist")
                sys.exit()
            else:
                log().error(err)
        else:
            log().info('Connected to MySQL database:' + cnx.database)
            cursor = cnx.cursor(buffered=True)
        return cursor,cnx


def commit_and_close_db_connection(cursor,cnx):

    # Commit changes and close cursor and connection

    try:
        cnx.commit()
        cursor.close()
        cnx.close()

    except Exception as e:
            log().info('There was a problem committing database changes or closing a database connection.')
            log().error('Error Code: ' + e)

    return


def create_run_id(session_info):
    date_obj = datetime.datetime.strptime(session_info['start_utc_human'], "%Y/%m/%d %H:%M:%S")
    run_id = session_info['platform_type'] + '_' + datetime.datetime.strftime(date_obj, dateTimeFormat)
    return run_id

def create_offset_id(session_start,sensor_id_db):
    date_obj = datetime.datetime.strptime(session_start, "%Y/%m/%d %H:%M:%S")
    offset_sid = sensor_id_db + '_' + datetime.datetime.strftime(date_obj, dateTimeFormat)
    return offset_sid

def hashfilelist(a_file, blocksize=65536):

    # Compute MD5 checksum of a file

    hasher = hashlib.md5()
    buf = a_file.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = a_file.read(blocksize)
    return hasher.hexdigest()

def formulate_query_string(data_indices,table_elements,table_name):

    # Formulate the query string for sensor_specific database tables

    query_str = ""
    var_str = "(meas_id,"
    value_str = " VALUES("

    for column in data_indices:
        var_str += table_elements[column] + ","
        value_str += "%s,"
        col = str(column)

    var_str = var_str[0:len(var_str) - 1] + ")"
    value_str += "%s)"
    query_str = ("INSERT INTO `" + table_name + "`" + var_str + value_str)

    return query_str


def populate_platform_state_table(run_id,platform_id,platform_state_info):
    # Open connection to database

    cursor, cnx = open_db_connection(config)

    for platform_state in platform_state_info :
        # These are ObjectState elements (see bottom of utility.py)
        # Should be able to load platform_state table from these elements.
        # These are already filtered down before this method as specified by the user.  So
        # if recorded at 50Hz might only be listed 5Hz or something.

        # Populate the platform_state database table

        try:

            datetime_str = datetime.datetime.fromtimestamp(platform_state.utc_time).strftime('%Y-%m-%d %H:%M:%S.%f')
            date_utc = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S.%f").date()
            time_utc = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S.%f").time()
            lat = str(platform_state.position[0])
            long = str(platform_state.position[1])
            position = (lat, long)
            altitude = platform_state.alt
            height_above_ground = platform_state.height_above_ground.item(0)
            height_agl = convert_NaN_to_None(height_above_ground)
            roll = convert_NaN_to_None(platform_state.roll)
            pitch = convert_NaN_to_None(platform_state.pitch)
            yaw = convert_NaN_to_None(platform_state.yaw)

            query = ("INSERT INTO platform_state(platform_id,run_id,date_time_utc,date_utc,time_utc,position,altitude,height_agl,roll,pitch,yaw) VALUES(%s,%s,%s,%s,%s,ST_PointFromText(CONCAT('POINT(',%s,' ',%s,')')),%s,%s,%s,%s,%s)")
            cursor.execute(query,(platform_id, run_id, datetime_str,date_utc, time_utc, lat, long, altitude, height_agl, roll, pitch, yaw))

        except Exception as e:
            if e.errno == errorcode.ER_DUP_ENTRY:
                log().error('Duplicate row found in database_table: platform_state.')
                sys.exit()
            else:
                log().info('There was a problem updating the platform_state table:')
                log().error(e)

    # Commit changes to table to the database and close the database connection

    log().info('Committing changes and closing connection to platform_state table...')
    commit_and_close_db_connection(cursor, cnx)

    return


def populate_run_table(run_id,platform_id,session_info):

    cursor, cnx = open_db_connection(config)

    log().info('Querying platform_state table for run coordinates...')

    try:
        run_query = ("SELECT MIN(x(position)),MAX(x(position)),MIN(y(position)),MAX(y(position)) FROM platform_state WHERE run_id LIKE %s")
        cursor.execute(run_query, (run_id,))

        for (latMin, latMax, lonMin, lonMax) in cursor:
            latMinStr = str(latMin)
            latMaxStr = str(latMax)
            lonMinStr = str(lonMin)
            lonMaxStr = str(lonMax)

        commit_and_close_db_connection(cursor, cnx)

    except Exception as e:
        log().info('There was a problem querying the platform_state table.')
        log().error('Error Code: ' + e)

    cursor, cnx = open_db_connection(config)

    try:

        run_folder_name = run_id

        run_start_date_str = datetime.datetime.fromtimestamp(session_info['start_utc']).strftime('%Y-%m-%d %H:%M:%S.%f')
        run_start_date_utc = datetime.datetime.strptime(run_start_date_str, "%Y-%m-%d %H:%M:%S.%f").date()
        run_start_time_utc = datetime.datetime.strptime(run_start_date_str, "%Y-%m-%d %H:%M:%S.%f").time()
        run_end_date_str = datetime.datetime.fromtimestamp(session_info['end_utc']).strftime('%Y-%m-%d %H:%M:%S.%f')
        run_end_date_utc = datetime.datetime.strptime(run_end_date_str, "%Y-%m-%d %H:%M:%S.%f").date()
        run_end_time_utc = datetime.datetime.strptime(run_end_date_str, "%Y-%m-%d %H:%M:%S.%f").time()

        log().info('Updating run table for run_id: '+run_id)
        run_insert = ("INSERT INTO run (run_id,platform_id,start_date_utc,start_time_utc,end_date_utc,end_time_utc,run_folder_name,run_polygon) "
                      "VALUES(%s,%s,%s,%s,%s,%s,%s,ST_PolygonFromText(CONCAT('POLYGON((',%s,' ',%s,',',%s,' ',%s,',',%s,' ',%s,',',%s,' ',%s,',',%s,' ',%s,'))')))")
        cursor.execute(run_insert, (run_id, platform_id, run_start_date_utc, run_start_time_utc, run_end_date_utc, run_end_time_utc, run_folder_name,latMinStr, lonMinStr, latMinStr, lonMaxStr, latMaxStr, lonMaxStr, latMaxStr, lonMinStr, latMinStr, lonMinStr))
        table_name = "run"

        log().info('Committing changes and closing connection to run database table...')
        commit_and_close_db_connection(cursor, cnx)

    except Exception as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            log().error('Duplicate row found in database table: run.')
            sys.exit()
        else:
            log().info('There was a problem updating the run table:')
            log().error(e)

    return


def populate_sensor_offsets_table(run_id,session,session_start):

    # Open connection to database

    cursor, cnx = open_db_connection(config)

    table_name = 'sensor_offsets'

    # Write sensor position and orientation offsets into the sensor_offsets table

    for sensor in session['sensors']:

        try:
            sensor_id_db = sensor['sensor_id'] + '_' + sensor['instrument_tag']
            x_offset = float(sensor['adjusted_position_offsets'][0])
            y_offset = float(sensor['adjusted_position_offsets'][1])
            z_offset = float(sensor['adjusted_position_offsets'][2])

            roll_offset = float(sensor['orientation_offsets'][0])
            pitch_offset = float(sensor['orientation_offsets'][1])
            yaw_offset = float(sensor['orientation_offsets'][2])

            offset_id = create_offset_id(session_start,sensor_id_db)

            query2 = (
            "INSERT INTO sensor_offsets(run_id,offset_id,sensor_id,x_offset,y_offset,z_offset,roll_offset,pitch_offset,yaw_offset) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)")
            cursor.execute(query2, (run_id, offset_id,sensor_id_db, x_offset, y_offset, z_offset, roll_offset, pitch_offset, yaw_offset))

        except Exception as e:
            if e.errno == errorcode.ER_DUP_ENTRY:
                log().error('Duplicate row found in database_table:' + table_name)
                sys.exit()
            else:
                log().error('There was a problem updating the sensor_offsets table:')
                log().error(e)

    log().info('Committing changes and closing connection to sensor_offsets database table.. ')
    commit_and_close_db_connection(cursor, cnx)

    return

def populate_sensor_tables(self,run_id,platform_id,session):

    # Update sensor-specific tables and associated measurement tabke

    for sensor in session['sensors']:

        sensor_id_db = sensor['sensor_id'] + '-' + sensor['instrument_tag']

        # Get the table names, data element names and indices (positions in list) of the data elements

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

        query_string = formulate_query_string(data_indices, table_elements, table_name)

        # Open connection to database for storing sensor readings and measurement table data.

        cursor, cnx = open_db_connection(config)

        meas_count = 0

        for reading in sensor['log_data']:

            # UTC time of the reading stored as seconds since epoch
            reading['time']

            try:

                # Populate the sensor-specific database table

                meas_count_str = str(meas_count).zfill(5)
                meas_dt = datetime.datetime.fromtimestamp(reading['time'])
                meas_dt_str = datetime.datetime.strftime(meas_dt, dateTimeFormat)
                meas_id = sensor_id_db + '_' + meas_dt_str + '_' + str(meas_count)

                # Initialize sensor_values string that will contain the VALUES passed to the database.
                sensor_values = [meas_id]

                # List of values that we should upload to database in the correct ordering.
                all_reading_values = reading['data']
                reading_values = [all_reading_values[i] for i in data_indices]

                sensor_values.extend(reading_values)
                query_values = tuple(sensor_values)

                cursor.execute(query_string, query_values)

                obs_state = reading['state']
                meas_count += 1

            except Exception as e:
                if e.errno == errorcode.ER_DUP_ENTRY:
                    log().error('Duplicate row found in database_table:' + table_name)
                    sys.exit()
                else:
                    log().error('There was a problem storing a reading in database table:' + table_name)
                    log().error(e)

            # ObjectState of sensor at time of reading (see bottom of utility.py)


            # Populate the measurement database table

            date_str = datetime.datetime.fromtimestamp(obs_state.utc_time).strftime('%Y-%m-%d %H:%M:%S.%f')
            date_utc = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f").date()
            time_utc = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f").time()
            lat = str(obs_state.position[0])
            long = str(obs_state.position[1])
            position = (lat, long)
            altitude = obs_state.alt.item(0)
            height_above_ground = obs_state.height_above_ground.item(0)
            height_agl = convert_NaN_to_None(height_above_ground)
            roll = convert_NaN_to_None(obs_state.roll)
            pitch = convert_NaN_to_None(obs_state.pitch)
            yaw = convert_NaN_to_None(obs_state.yaw)

            try:

                query1 = (
                    "INSERT INTO measurement(platform_id,run_id,sensor_id,meas_id,date_utc,time_utc,position,altitude,height_agl,roll,pitch,yaw) VALUES(%s,%s,%s,%s,%s,%s,ST_PointFromText(CONCAT('POINT(',%s,' ',%s,')')),%s,%s,%s,%s,%s)")
                cursor.execute(query1, (platform_id, run_id, sensor_id_db, meas_id, date_utc, time_utc, lat, long, altitude, height_agl,roll,pitch, yaw))

            except mysql.connector.Error as err:
                log().info('There was a problem updating the measurements table:')
                log().info(err)

        # Make sure data is committed to the database and close the database connection


        log().info('Committing changes and closing connection to database table: ' + table_name)
        commit_and_close_db_connection(cursor, cnx)
    return

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
        self.sensor_type_to_table_name = {'canon_edsdk': 'image',
                                          'test_sensor_python': 'test',
                                          'gps_trmb_test': 'position',
                                         }

        # The values are data names (defined in sensor_metadata.yaml) listed in the order they appear in the database table.
        # The names don't have to match the database fields exactly, just the ordering matters.
        #self.sensor_type_to_table_elements = {'canon_edsdk':['meas_key','meas_id','image_file_name','md5sum'],
        #                                     'test_sensor_python': ['meas_key','meas_id','counter','rand_int', 'rand_float'],
        #                                     'gps_trmb_test': ['meas_key','meas_id','latitude'],
        #                                     }
        self.sensor_type_to_table_elements = {'canon_edsdk': ['image_name'],
                                              'test_sensor_python': ['counter', 'rand_int', 'rand_float'],
                                              'gps_trmb_test': ['latitude'],}

#    'test_sensor_python': ['utc_time', 'latitude', 'longitude', 'altitude', 'roll', 'pitch', 'yaw', 'height', 'counter',
#                           'rand_int', 'rand_float'],

    def upload(self, session):
        start_time = time.time()

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

        # Formulate run_id: platform_type + start_date + start_time

        run_id=create_run_id(session_info)
        log().info('Uploading data for run_id: '+run_id)
        session_start=session_info['start_utc_human']

        # Formulate the platform_id: platform_type + platform_tag

        platform_id=session_info['platform_type'] + '-' + session_info['platform_tag']

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
        
            # Note use 'adjusted_position_offsets' instead of 'position_offsets'.
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

        # Populate the platform_state database table

        platform_state_info = session['platform_states']
        populate_platform_state_table(run_id, platform_id, platform_state_info)

        # Populate the sensor offsets table

        populate_sensor_offsets_table(run_id, session,session_start)

        # Populate database tables for all sensors that are configured in the system

        populate_sensor_tables(self,run_id,platform_id, session)

        # Write entry into run_table

        populate_run_table(run_id, platform_id,session_info)

        log().info("Database Upload Time: --- %s seconds ---" % round(time.time() - start_time))

        return True # successful upload

