
import struct
import math

class GlobID:
    
    AssertMessage = 0
    DebugMessage = 1
    UserData = 9

class ImuGlob(object):
    
    @property
    def id(self):
        return self.__class__.id
        
    @classmethod
    def from_bytes(cls, data_bytes, instance=1):
        obj = cls(instance=instance)
        obj.unpack(data_bytes)
        return obj
        
class AssertMessage(ImuGlob):
    
    # Unique class ID
    id = GlobID.AssertMessage
    
    continue_action = 0
    restart_action = 1
    stop_action = 2
    
    # Struct format for packing/unpacking. Little-endian no padding.
    data_format = '<I200sI'
    
    def __init__(self, instance=1):
        '''Constructor'''
        self.instance = instance

    def unpack(self, data_bytes):
        
        self.action, self.message, valid = struct.unpack(AssertMessage.data_format, data_bytes)
        self.valid = bool(valid)

class DebugMessage(ImuGlob):
    
    # Unique class ID
    id = GlobID.DebugMessage
    
    # Struct format for packing/unpacking. Little-endian no padding.
    data_format = '<200sI'
    
    def __init__(self, instance=1):
        '''Constructor'''
        self.instance = instance

    def unpack(self, data_bytes):
        
        self.message, valid = struct.unpack(DebugMessage.data_format, data_bytes)
        self.valid = bool(valid)

class UserData(ImuGlob):
    
    # Unique class ID
    id = GlobID.UserData
    
    # Struct format for packing/unpacking. Little-endian no padding.
    data_format = '<ffff'
    
    def __init__(self, instance=1):
        '''Constructor'''
        self.instance = instance

    def unpack(self, data_bytes):
        
        values = struct.unpack(UserData.data_format, data_bytes)
        
        self.roll = float(values[0])
        self.pitch = float(values[1])
        self.yaw = float(values[2])
        self.battery = float(values[3])

