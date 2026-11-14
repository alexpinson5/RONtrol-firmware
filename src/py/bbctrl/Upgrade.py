################################################################################
#                                                                              #
#                 This file is part of the Buildbotics firmware.               #
#                                                                              #
#        Copyright (c) 2015 - 2023, Buildbotics LLC, All rights reserved.      #
#                                                                              #
#         This Source describes Open Hardware and is licensed under the        #
#                                 CERN-OHL-S v2.                               #
#                                                                              #
#         You may redistribute and modify this Source and make products        #
#    using it under the terms of the CERN-OHL-S v2 (https:/cern.ch/cern-ohl).  #
#           This Source is distributed WITHOUT ANY EXPRESS OR IMPLIED          #
#    WARRANTY, INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS  #
#     FOR A PARTICULAR PURPOSE. Please see the CERN-OHL-S v2 for applicable    #
#                                  conditions.                                 #
#                                                                              #
#                Source location: https://github.com/buildbotics               #
#                                                                              #
#      As per CERN-OHL-S v2 section 4, should You produce hardware based on    #
#    these sources, You must maintain the Source Location clearly visible on   #
#    the external case of the CNC Controller or other product you make using   #
#                                  this Source.                                #
#                                                                              #
#                For more information, email info@buildbotics.com              #
#                                                                              #
################################################################################


'''
Runs a firmware upgrade or update script and reports when it fails.

The script runs in its own systemd scope so it survives update-bbctrl
stopping bbctrl.  On success bbctrl is stopped, and later restarted, before
the script ends, so a script seen to exit while bbctrl still runs has failed.

Output goes to a file rather than a pipe.  A pipe would break once bbctrl
stops, and the install would die writing to it.
'''

import subprocess
import tempfile
from typing import List

__all__ = ['Upgrade', 'failure_message']

POLL_SECS    = 2
OUTPUT_LINES = 4


def failure_message(returncode: int, output: str) -> str:
    'User-facing message for a script that exited without installing.'
    lines = [line for line in output.splitlines() if line.strip()]
    lines = lines[-OUTPUT_LINES:]

    msg = 'Firmware upgrade failed'
    if returncode: msg += ' (exit code %d)' % returncode
    else: msg += ', nothing was installed'

    if lines: msg += ':\n' + '\n'.join(lines)
    return msg


class Upgrade(object):
    def __init__(self, ctrl, cmd: List[str]):
        self.ctrl = ctrl
        self.log = ctrl.log.get('Upgrade')
        self.output = tempfile.TemporaryFile(mode = 'w+')

        ctrl.lcd.goodbye('Upgrading firmware')
        self.proc = subprocess.Popen(
            ['systemd-run', '--unit=bbctrl-update', '--scope',
             '--slice=bbctrl-update'] + cmd,
            stdout = self.output, stderr = subprocess.STDOUT)

        ctrl.ioloop.call_later(POLL_SECS, self._poll)


    def _poll(self) -> None:
        returncode = self.proc.poll()
        if returncode is None:
            self.ctrl.ioloop.call_later(POLL_SECS, self._poll)
            return

        self.output.seek(0)
        output = self.output.read()
        self.output.close()

        self.ctrl.lcd.resume()
        self.log.error(failure_message(returncode, output))
