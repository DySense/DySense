
pyinstaller ../../bin/DySense.py ^
--clean ^
--noconfirm ^
--windowed ^
--runtime-hook rthook_pyqt4.py ^
--icon=../resources/dysense_logo_no_text_icon.ico