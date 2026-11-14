'''Tests for the G-code the Zero and Set Position buttons send on a homed
axis: it sets the active coordinate system's offset, which is persisted,
rather than a G92 offset, which a reset loses.'''

import pytest

from bbctrl.ProgramSetPosition import coord_system_number, work_offset_gcode


@pytest.mark.parametrize('code, number', [
    (540, 1), (550, 2), (560, 3), (570, 4), (580, 5), (590, 6),
    (591, 7), (592, 8), (593, 9),
])
def test_reported_coordinate_system_maps_to_its_g10_p_number(code, number):
    assert coord_system_number(code) == number


def test_zero_in_g54_sets_the_g54_offset():
    assert work_offset_gcode('x', 0, 540) == 'G10 L20 P1 x0.000000'


def test_set_position_in_g56_sets_the_g56_offset():
    assert work_offset_gcode('z', -12.5, 560) == 'G10 L20 P3 z-12.500000'


def test_set_position_never_uses_g92():
    for code in (540, 550, 560, 570, 580, 590, 591, 592, 593):
        assert 'G92' not in work_offset_gcode('y', 1, code)
