---------------------------
Windows Instructions
---------------------------

Note: if you've already generated a .spec file and you want to release a new version you can skip running dysense_windows.bat and just use the spec file you already have.

Note: if you ever get a PermissionDenied error then try running the command again or if that doesnt work you can open the command shell in Adminstrator Mode.

0) Update the DySense version in version.py.  Look in the repository to see what changes have been made since the last release.  If overall it's a conceptually signficant difference then increase the <major> number, if it's a conceptually small change(s) then increase the <minor> number.  If its only bug fixes then increase the <patch> number.

1) Run dysense_windows.bat to generate a spec file.

2) Make the changes listed below in the SPEC CHANGES section.

3) Run the spec file directly with 'pyinstaller dysense_ui.spec'.  If it asks if you want to remove all output directory contents hit <enter> (yes is the default choice)

4) In the 'added_files' list in the SPEC CHANGES section there are folders specified by ../foldername/ (e.g. ../metadata/).  These need to be one level above dysense_ui.exe.  To do this first select these directories in dist/dysense_ui/, and cut and paste them into dist/ (to move them up one level)

5) Rename dist/ to DySense-<version>-<OS>-<arch>/ where <version> matches the AppVersion in the version.py.  <OS> is either 'win' 'mac' or 'lin' and <arch> is either 'x86' or 'x64'.  Look at a previous release for an example.

6) Upload to GitHub releases with the change notes. 

---------------------------
SPEC CHANGES
---------------------------
# Add this list of directories to copy.
added_files = [
         ( '../metadata/', 'metadata' ),
         ( '../nmea_logs/', 'nmea_logs' ),
         ( '../resources/', 'resources' ),
         ( '../sensors/', 'sensors' ),
         ]
         
 a = Analysis(['..\\source\\dysense_ui.py'],
     ...
     datas=added_files, # <-- change None to added_files
     ...)