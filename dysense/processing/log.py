# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import os
import sys
import logging

def setup_logging(output_path, file_log_level, console_log_level):
    '''Setup logging. Always to log file, optionally to command line if console_level isn't None. Return log.'''

    log = logging.getLogger("processing")
    log.setLevel(logging.DEBUG)
    handler = logging.FileHandler(os.path.join(output_path, time.strftime("processing.log")))
    handler.setLevel(file_log_level)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)-5.5s]  %(message)s'))
    log.addHandler(handler)

    if console_log_level is not None:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(console_log_level)
        handler.setFormatter(logging.Formatter('[%(levelname)-5.5s] %(message)s'))
        log.addHandler(handler)

    return log

def log():
    '''Return main log that should be used by this package.'''
    return logging.getLogger('processing')