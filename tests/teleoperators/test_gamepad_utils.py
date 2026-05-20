#!/usr/bin/env python

# Copyright 2025 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from lerobot.teleoperators.gamepad.gamepad_utils import (
    DUNEFOX_HID_REPORT_DESCRIPTOR,
    LOGITECH_HID_REPORT_DESCRIPTOR,
    episode_status_from_buttons,
    parse_hid_gamepad_report,
)
from lerobot.teleoperators.utils import TeleopEvents


def test_parse_dunefox_hid_report_descriptor():
    report = [160, 64, 128, 192, 2, 64, 9, 0, 100]

    parsed_report = parse_hid_gamepad_report(report, DUNEFOX_HID_REPORT_DESCRIPTOR, deadzone=0.1)

    assert parsed_report is not None
    assert parsed_report.axes == {
        "left_x": 0.25,
        "left_y": -0.5,
        "right_x": 0.0,
        "right_y": 0.5,
    }
    assert parsed_report.buttons["y"] is True
    assert parsed_report.buttons["rb"] is True
    assert parsed_report.buttons["rt_click"] is True
    assert parsed_report.buttons["dpad_left"] is True
    assert parsed_report.buttons["dpad_up"] is False
    assert episode_status_from_buttons(
        parsed_report.buttons,
        DUNEFOX_HID_REPORT_DESCRIPTOR.actions,
    ) == TeleopEvents.SUCCESS
    assert DUNEFOX_HID_REPORT_DESCRIPTOR.motion.get_deltas(parsed_report.axes, 1.0, 1.0, 1.0) == (
        0.5,
        -0.25,
        -0.5,
    )


def test_parse_logitech_hid_report_descriptor_preserves_existing_layout():
    report = [0, 128, 0, 128, 255, 1 << 5, 12, 0]

    parsed_report = parse_hid_gamepad_report(report, LOGITECH_HID_REPORT_DESCRIPTOR, deadzone=0.1)

    assert parsed_report is not None
    assert parsed_report.axes == {
        "left_y": 0.0,
        "left_x": -1.0,
        "right_x": 0.0,
        "right_y": 127 / 128,
    }
    assert parsed_report.buttons["failure"] is True
    assert parsed_report.buttons["open_gripper"] is True
    assert parsed_report.buttons["close_gripper"] is True
    assert episode_status_from_buttons(
        parsed_report.buttons,
        LOGITECH_HID_REPORT_DESCRIPTOR.actions,
    ) == TeleopEvents.FAILURE
    assert LOGITECH_HID_REPORT_DESCRIPTOR.motion.get_deltas(parsed_report.axes, 1.0, 1.0, 1.0) == (
        1.0,
        -0.0,
        -127 / 128,
    )


def test_dunefox_descriptor_matches_vid_pid():
    assert DUNEFOX_HID_REPORT_DESCRIPTOR.matches_device(
        {"vendor_id": 0x04B5, "product_id": 0x2413, "product_string": None}
    )
