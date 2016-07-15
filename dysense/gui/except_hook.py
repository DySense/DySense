# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import sys
import traceback
import cStringIO
from PyQt4 import QtGui
from PyQt4.QtGui import QStyle

from dysense.core.utility import utf_8_encoder, make_unicode
from dysense.core.version import app_version

def excepthook(excection_type, excection_value, traceback_object):
    """Callback for any unhandled exceptions. To use set sys.excepthook = excepthook"""
    separator = '-' * 50
    body_text = "An unhandled exception occurred.\nPlease report the problem on github issue tracker.\n" \
                "(Hit Ctrl+C to copy text from dialog)"
    current_time = time.strftime("%Y-%m-%d, %H:%M:%S")
    version_info = "DySense Version {}".format(app_version)
    
    # Get useful information from traceback object
    traceback_file = cStringIO.StringIO()
    traceback.print_tb(traceback_object, None, traceback_file)
    traceback_file.seek(0)
    traceback_info = traceback_file.read()
    
    error_message = '{}: \n{}'.format(excection_type, make_unicode(excection_value))
    sections = [body_text, separator, version_info, current_time, separator,
                error_message, separator, traceback_info]
    unicode_sections = [make_unicode(s) for s in sections]
    dialog_message = '\n'.join(unicode_sections)

    popup = QtGui.QMessageBox()
    popup.setText(dialog_message)
    popup.setWindowTitle('Error')
    popup.setWindowIcon(popup.style().standardIcon(QStyle.SP_MessageBoxCritical))
    popup.exec_()
    # TODO figure out why this hangs sometimes
    #sys.exit(1)