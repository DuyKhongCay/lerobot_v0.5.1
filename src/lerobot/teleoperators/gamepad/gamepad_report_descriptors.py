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

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..utils import TeleopEvents


@dataclass(frozen=True)
class GamepadMotionMapping:
    """Map normalized logical axes to robot motion deltas."""

    delta_x_axis: str = "left_x"
    delta_y_axis: str = "left_y"
    delta_z_axis: str = "right_y"
    delta_x_scale: float = -1.0
    delta_y_scale: float = -1.0
    delta_z_scale: float = -1.0

    def get_deltas(
        self,
        axes: Mapping[str, float],
        x_step_size: float,
        y_step_size: float,
        z_step_size: float,
    ) -> tuple[float, float, float]:
        delta_x = axes.get(self.delta_x_axis, 0.0) * self.delta_x_scale * x_step_size
        delta_y = axes.get(self.delta_y_axis, 0.0) * self.delta_y_scale * y_step_size
        delta_z = axes.get(self.delta_z_axis, 0.0) * self.delta_z_scale * z_step_size
        return delta_x, delta_y, delta_z


@dataclass(frozen=True)
class GamepadActionMapping:
    """Map logical button names to teleop actions."""

    success: str = "success"
    failure: str = "failure"
    rerecord_episode: str = "rerecord_episode"
    intervention: str = "intervention"
    open_gripper: str = "open_gripper"
    close_gripper: str = "close_gripper"


@dataclass(frozen=True)
class PygameAxisBinding:
    """A pygame joystick axis binding."""

    index: int
    scale: float = 1.0


@dataclass(frozen=True)
class PygameGamepadReportDescriptor:
    """Logical gamepad layout for pygame/SDL input."""

    name: str
    axes: Mapping[str, PygameAxisBinding]
    buttons: Mapping[str, int]
    actions: GamepadActionMapping
    motion: GamepadMotionMapping

    def button_name(self, button_index: int) -> str | None:
        for name, index in self.buttons.items():
            if index == button_index:
                return name
        return None


@dataclass(frozen=True)
class HIDAxisBinding:
    """A byte in a HID input report interpreted as a centered joystick axis."""

    byte_index: int
    center: float = 128.0
    scale: float = 128.0
    invert: bool = False

    def normalize(self, report: Sequence[int]) -> float:
        value = (report[self.byte_index] - self.center) / self.scale
        return -value if self.invert else value


@dataclass(frozen=True)
class HIDButtonBinding:
    """A HID button binding represented by a bit mask, exact values, or threshold."""

    byte_index: int
    mask: int | None = None
    values: tuple[int, ...] = ()
    threshold: int | None = None

    def is_pressed(self, report: Sequence[int]) -> bool:
        if self.byte_index >= len(report):
            return False

        value = report[self.byte_index]
        if self.mask is not None and value & self.mask:
            return True
        if self.values and value in self.values:
            return True
        return self.threshold is not None and value >= self.threshold


@dataclass(frozen=True)
class HIDDpadBinding:
    """A HID hat switch/D-pad byte mapped to logical direction buttons."""

    byte_index: int
    idle_value: int
    directions: Mapping[str, int]

    def parse(self, report: Sequence[int]) -> dict[str, bool]:
        if self.byte_index >= len(report):
            return {name: False for name in self.directions}

        value = report[self.byte_index]
        return {name: value == direction_value for name, direction_value in self.directions.items()}


@dataclass(frozen=True)
class HIDGamepadReportDescriptor:
    """Logical layout for a HID gamepad input report."""

    name: str
    report_length: int
    axes: Mapping[str, HIDAxisBinding]
    buttons: Mapping[str, HIDButtonBinding]
    actions: GamepadActionMapping
    motion: GamepadMotionMapping
    product_strings: tuple[str, ...] = ()
    vendor_id: int | None = None
    product_id: int | None = None
    dpad: HIDDpadBinding | None = None

    def matches_device(self, device: Mapping[str, object]) -> bool:
        if (
            self.vendor_id is not None
            and self.product_id is not None
            and device.get("vendor_id") == self.vendor_id
            and device.get("product_id") == self.product_id
        ):
            return True

        product_string = str(device.get("product_string") or "")
        return any(product_name in product_string for product_name in self.product_strings)


@dataclass(frozen=True)
class ParsedGamepadReport:
    axes: dict[str, float]
    buttons: dict[str, bool]


LOGITECH_PYGAME_REPORT_DESCRIPTOR = PygameGamepadReportDescriptor(
    name="logitech_pygame",
    axes={
        "left_y": PygameAxisBinding(index=0),
        "left_x": PygameAxisBinding(index=1),
        "right_y": PygameAxisBinding(index=3),
    },
    buttons={
        "rerecord_episode": 0,
        "failure": 1,
        "success": 3,
        "intervention": 5,
        "close_gripper": 6,
        "open_gripper": 7,
    },
    actions=GamepadActionMapping(),
    motion=GamepadMotionMapping(delta_x_axis="left_x", delta_y_axis="left_y", delta_z_axis="right_y"),
)

LOGITECH_HID_REPORT_DESCRIPTOR = HIDGamepadReportDescriptor(
    name="logitech_hid",
    report_length=8,
    product_strings=("Logitech", "Xbox", "PS4", "PS5"),
    axes={
        "left_y": HIDAxisBinding(byte_index=1),
        "left_x": HIDAxisBinding(byte_index=2),
        "right_x": HIDAxisBinding(byte_index=3),
        "right_y": HIDAxisBinding(byte_index=4),
    },
    buttons={
        "success": HIDButtonBinding(byte_index=5, mask=1 << 7),
        "failure": HIDButtonBinding(byte_index=5, mask=1 << 5),
        "rerecord_episode": HIDButtonBinding(byte_index=5, mask=1 << 4),
        "intervention": HIDButtonBinding(byte_index=6, values=(2, 6, 10, 14)),
        "open_gripper": HIDButtonBinding(byte_index=6, values=(8, 10, 12)),
        "close_gripper": HIDButtonBinding(byte_index=6, values=(4, 6, 12)),
    },
    actions=GamepadActionMapping(),
    motion=GamepadMotionMapping(delta_x_axis="left_x", delta_y_axis="left_y", delta_z_axis="right_y"),
)

DUNEFOX_HID_REPORT_DESCRIPTOR = HIDGamepadReportDescriptor(
    name="dunefox_hid",
    report_length=9,
    product_strings=("DuneFox", "Dunefox", "dunefox"),
    vendor_id=0x04B5,
    product_id=0x2413,
    axes={
        "left_x": HIDAxisBinding(byte_index=0),
        "left_y": HIDAxisBinding(byte_index=1),
        "right_x": HIDAxisBinding(byte_index=2),
        "right_y": HIDAxisBinding(byte_index=3),
    },
    buttons={
        "a": HIDButtonBinding(byte_index=6, mask=128),
        "b": HIDButtonBinding(byte_index=6, mask=64),
        "x": HIDButtonBinding(byte_index=6, mask=16),
        "y": HIDButtonBinding(byte_index=6, mask=8),
        "lb": HIDButtonBinding(byte_index=6, mask=2),
        "rb": HIDButtonBinding(byte_index=6, mask=1),
        "lt_click": HIDButtonBinding(byte_index=5, mask=128),
        "rt_click": HIDButtonBinding(byte_index=5, mask=64),
    },
    actions=GamepadActionMapping(
        success="y",
        failure="x",
        rerecord_episode="a",
        intervention="rb",
        open_gripper="rt_click",
        close_gripper="lt_click",
    ),
    motion=GamepadMotionMapping(delta_x_axis="left_y", delta_y_axis="left_x", delta_z_axis="right_y"),
    dpad=HIDDpadBinding(
        byte_index=4,
        idle_value=8,
        directions={
            "dpad_up": 0,
            "dpad_down": 4,
            "dpad_left": 2,
            "dpad_right": 6,
        },
    ),
)

PYGAME_REPORT_DESCRIPTORS = {
    "logitech": LOGITECH_PYGAME_REPORT_DESCRIPTOR,
}

HID_REPORT_DESCRIPTORS = {
    "logitech": LOGITECH_HID_REPORT_DESCRIPTOR,
    "dunefox": DUNEFOX_HID_REPORT_DESCRIPTOR,
}


def get_pygame_report_descriptor(name: str) -> PygameGamepadReportDescriptor:
    try:
        return PYGAME_REPORT_DESCRIPTORS[name]
    except KeyError as exc:
        available = ", ".join(sorted(PYGAME_REPORT_DESCRIPTORS))
        raise ValueError(f"Unknown pygame gamepad descriptor '{name}'. Available descriptors: {available}") from exc


def get_hid_report_descriptor(name: str) -> HIDGamepadReportDescriptor:
    try:
        return HID_REPORT_DESCRIPTORS[name]
    except KeyError as exc:
        available = ", ".join(sorted(HID_REPORT_DESCRIPTORS))
        raise ValueError(f"Unknown HID gamepad descriptor '{name}'. Available descriptors: {available}") from exc


def _apply_deadzone(value: float, deadzone: float) -> float:
    return 0.0 if abs(value) < deadzone else value


def parse_hid_gamepad_report(
    report: Sequence[int],
    report_descriptor: HIDGamepadReportDescriptor,
    deadzone: float,
) -> ParsedGamepadReport | None:
    """Parse a raw HID input report using a controller-specific descriptor."""
    if not report or len(report) < report_descriptor.report_length:
        return None

    axes = {
        name: _apply_deadzone(axis.normalize(report), deadzone)
        for name, axis in report_descriptor.axes.items()
        if axis.byte_index < len(report)
    }
    buttons = {
        name: button.is_pressed(report)
        for name, button in report_descriptor.buttons.items()
        if button.byte_index < len(report)
    }
    if report_descriptor.dpad is not None:
        buttons.update(report_descriptor.dpad.parse(report))

    return ParsedGamepadReport(axes=axes, buttons=buttons)


def read_pygame_gamepad_state(
    joystick,
    report_descriptor: PygameGamepadReportDescriptor,
    deadzone: float,
) -> ParsedGamepadReport:
    """Read pygame joystick state using a controller-specific descriptor."""
    axes = {
        name: _apply_deadzone(joystick.get_axis(axis.index) * axis.scale, deadzone)
        for name, axis in report_descriptor.axes.items()
    }
    buttons = {
        name: bool(joystick.get_button(button_index))
        for name, button_index in report_descriptor.buttons.items()
    }
    return ParsedGamepadReport(axes=axes, buttons=buttons)


def episode_status_from_button(button_name: str | None, actions: GamepadActionMapping) -> TeleopEvents | None:
    if button_name == actions.success:
        return TeleopEvents.SUCCESS
    if button_name == actions.failure:
        return TeleopEvents.FAILURE
    if button_name == actions.rerecord_episode:
        return TeleopEvents.RERECORD_EPISODE
    return None


def episode_status_from_buttons(
    buttons: Mapping[str, bool],
    actions: GamepadActionMapping,
) -> TeleopEvents | None:
    for button_name in (actions.success, actions.failure, actions.rerecord_episode):
        if buttons.get(button_name):
            return episode_status_from_button(button_name, actions)
    return None
