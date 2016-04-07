
# Update python code to match designer file.
#Capable of updating main window and sensor view widget depending on which line is commented out
import subprocess
process = subprocess.Popen('pyuic4 dysense_designer.ui -o dysense_main_window_designer.py', shell=True, stdout=subprocess.PIPE)
process = subprocess.Popen('pyuic4 sensor_view_widget.ui -o sensor_view_widget_designer.py', shell=True, stdout=subprocess.PIPE)
process.wait()
print process.returncode

