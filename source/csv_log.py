#!/usr/bin/env python
# -*- coding: utf-8 -*-
#from __future__ import unicode_literals

import csv
from _ctypes import ArgumentError
from utility import make_utf8

class CSVLog:
    '''
    Log each sensor data sample on a new line separated by commas with a \r\n line terminator.
    If any element of the data contains a comma that element is enclosed in quotes.
    '''
    
    def __init__(self, file_path, buffer_size):
        '''
        Save properties for creating log file when first data is received.
        
        file_path must not already exist on the file system or an exception will be thrown.
        
        Buffer size is how many samples to buffer before writing (and flushing) to file.
        buffer_size =  0 or 1  flush every sample to file right when it's received.
        buffer_size =  n       buffer 'n' samples before flushing all of them to the file.
        '''
        self.file_path = file_path
        self.buffer_size = buffer_size
        self.buffer = []
        self.file = None
        
    def write(self, data):
        '''Write data to file or buffer it depending on class settings. Data is a list.'''
                
        if (data is None) or (len(data) == 0):
            # Create blank one element tuple so it's obvious in log that no data was received.
            raise Exception(u"Data can't be empty.")

        for i, val in enumerate(data):
            if type(data[i]) == float:
                # Convert all floats using built in representation function.  This avoids loss of precision
                #  due to the way floats are printed in python.
                val = repr(val)
            # Make sure all data is encoded as utf8.
            data[i] = make_utf8(val)
        
        # Check if all we need to do is buffer data.
        if self.buffer_size > 1:
            if len(self.buffer) < (self.buffer_size - 1):
                self.buffer.append(data)
                return
             
        # Make sure file is open so we can write to it.
        if self.file is None:
            self.file = open(self.file_path, 'wb')
            self.writer = csv.writer(self.file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            
        if len(self.buffer) > 0:
            # Write all the data we've been saving.
            self.writer.writerows(self.buffer)
            self.buffer = []
                    
        # Write current sample data.
        self.writer.writerow(data)
        
        # Make sure data gets written in case of power failure.
        self.file.flush()
            
    def handle_metadata(self, sensor_type, sensor_id, metadata): 
        '''Store metadata in buffer to be written out the first time handle_data is called.'''
        if len(metadata) == 0:
            raise ArgumentError(u'Metadata must contain at least one element')
        
        metadata[0] = u'#' + make_utf8(metadata[0])
        self.buffer.append(metadata)
        
    def terminate(self):
        '''Write any buffered data to file and then close file.'''
        if self.file is None:
            return # Never received any data.
        
        if len(self.buffer) > 1:
            self.writer.writerows(self.buffer)
        
        self.file.flush()
        self.file.close()
        self.file = None
        