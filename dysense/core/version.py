# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# All versions follow the <major>.<minor>.<patch> scheme with Semantic Versioning.

app_version = '1.1.0' # Version for entire application

output_version = '2.0.0' # Version for session output structure / data.

# Protocol versions
m2c_version = '2.0.0' # Manager-Controller protocol
s2c_version = '2.0.0' # Sensor-Controller protocol
p2m_version = '2.0.0' # Presenter-Manager protocol 


class SemanticVersion(object):
    
    def __init__(self, version):
        
        parts = version.split('.')
        
        try:
            self.major = int(parts[0])
            self.minor = int(parts[1])
            self.fix = int(parts[2])
        except (IndexError, ValueError):
            raise ValueError("Invalid version: {}".format(version))

    def __str__(self):
        return 'V({}.{}.{})'.format(self.major, self.minor, self.fix)
    
    __repr__ = __str__
