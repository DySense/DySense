Run from source:

 - Install Git and download the repository using the following command "git clone https://github.com/Phenomics-KSU/DySense.git"
 - Install Python 2.7
 - Install setuptools https://pypi.python.org/pypi/setuptools#installation-instructions If on Windows follow the [Windows (Simplified)] instructions of simply downloading and running ez_setup.py)
 - In a command shell navigate to the base DySense folder (e.g. C:/Users/AccountName/Documents/DySense) and run "setup.py install" (or "setup.py develop" if you'll be making changes)
 - Look at the output.  If any dependency (e.g. pyzmq) failed to installed then you'll have to go out and install it yourself.  
 - Download and install PyQt4.  This can't be installed automatically using the setup.py file.  Make sure to download the 32 or 64 bit that's consistent with what version of python you have installed.  If you're not sure which python version you have you can tell from one of the top two answers here http://stackoverflow.com/questions/1405913/how-do-i-determine-if-my-python-shell-is-executing-in-32bit-or-64bit-mode-on-os.
 - Run "dysense_ui.py" which should launch the main window.
 - Optionally you can create a shortcut on your Desktop to the "dysense_ui.py" file. 
