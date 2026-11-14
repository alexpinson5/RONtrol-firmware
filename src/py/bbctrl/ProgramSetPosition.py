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

from .ProgramMDI import *

__all__ = ['ProgramSetPosition', 'coord_system_number', 'work_offset_gcode']


def coord_system_number(code: int) -> int:
  '''The G10 P number for a reported coord_system: 540 (G54) is 1, 590 (G59)
  is 6 and 591 (G59.1) is 7.'''
  if code <= 590: return code // 10 - 53
  return code - 584


def work_offset_gcode(axis: str, position: float, coord_system: int) -> str:
  '''G-code that sets the active coordinate system's offset so the current
  position reads as position.  Unlike G92, G10 changes the offset table, which
  is saved and survives a reset.'''
  return 'G10 L20 P%d %s%f' % (coord_system_number(coord_system), axis,
                                position)


class ProgramSetPosition(ProgramMDI):
  def __init__(self, ctrl, axis, position):
    axis  = axis.lower()
    state = ctrl.state

    if state.is_axis_homed(axis):
      # If homed, change the work offset rather than the absolute position
      cmd = work_offset_gcode(axis, position, state.get('coord_system', 540))

    elif state.is_axis_enabled(axis):
      # Set absolute position via planner
      target = position + state.get('offset_' + axis)
      cmd = 'G28.3 %s%f\nG28.2 %s0' % (axis, target, axis)

    else: raise Exception('Cannot set position, %s axis not enabled' % axis)

    super().__init__(ctrl, cmd)
