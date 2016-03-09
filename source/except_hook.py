from ui_settings import ui_version
import time
import sys
import traceback
import cStringIO
from PyQt4 import QtGui
from PyQt4.QtGui import QStyle

def excepthook(excection_type, excection_value, traceback_object):
    """Callback for any unhandled exceptions. To use set sys.excepthook = excepthook"""
    separator = '-' * 50
    body_text = "An unhandled exception occurred.\nPlease report the problem on github issue tracker.\n" \
                "(Hit Ctrl+C to copy text from dialog)"
    current_time = time.strftime("%Y-%m-%d, %H:%M:%S")
    version_info = "GUI Version {}".format(ui_version)
    
    # Get useful information from traceback object
    traceback_file = cStringIO.StringIO()
    traceback.print_tb(traceback_object, None, traceback_file)
    traceback_file.seek(0)
    traceback_info = traceback_file.read()
    
    error_message = '{}: \n{}'.format(excection_type, excection_value)
    sections = [body_text, separator, version_info, current_time, separator,
                error_message, separator, traceback_info]
    dialog_message = '\n'.join(sections)

    popup = QtGui.QMessageBox()
    popup.setText(dialog_message)
    popup.setWindowTitle('Error')
    popup.setWindowIcon(popup.style().standardIcon(QStyle.SP_MessageBoxCritical))
    popup.exec_()
    sys.exit(1)