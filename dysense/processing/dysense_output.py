# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from dysense.core.version import SemanticVersion
from dysense.processing.utility import unicode_csv_reader
from dysense.processing.output_versions.dysense_output_v1 import SessionOutputV1
from dysense.processing.output_versions.dysense_output_v2 import SessionOutputV2
from dysense.processing.log import log

class SessionOutputFactory(object):
    '''
    Provide interface for reading different parts of a DySense session directory.
    Before using data user should verify that session_valid property is True.
    All files are assumed to be saved in UTF8 format.
    '''
    @classmethod
    def get_object(cls, session_path, default_version=SemanticVersion('1.0.0')):
        '''Return SessionOutputX class where X corresponds to the detected output version in session_path.'''

        # Associate a 'major' version number with the class used to read the session contents.
        version_to_output_class = { 1: SessionOutputV1,
                                    2: SessionOutputV2 }

        try:
            output_version = cls._read_output_version(session_path)
            log().debug('Output version {}'.format(output_version))
        except IOError:
            log().error("Session info file not found")
            return None

        if output_version is None:
            log().warn("No output version detected. Using default version {}".format(default_version))
            output_version = default_version

        try:
            OutputClass = version_to_output_class[output_version.major]
            session_output = OutputClass(session_path, output_version)
        except KeyError:
            log().error("Output version {} not supported by this version of DySense. Latest supported is {}.".format(output_version.major, max(version_to_output_class.keys())))
            return None

        return session_output

    @classmethod
    def _read_output_version(cls, session_path):
        '''Return SemanticVersion of session at session path or None if not found.'''

        session_info_file_path = os.path.join(session_path, 'session_info.csv')

        with open(session_info_file_path, 'r') as session_info_file:
            file_reader = unicode_csv_reader(session_info_file)
            for line_num, line in enumerate(file_reader):

                if len(line) < 2:
                    continue

                info_name = line[0]
                info_value = line[1]

                if info_name.lower() == 'output_version':
                    return SemanticVersion(info_value)

        return None # output version not found
