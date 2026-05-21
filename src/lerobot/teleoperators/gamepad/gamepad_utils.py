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

import logging
from typing import TYPE_CHECKING

from lerobot.utils.import_utils import _hidapi_available, _pygame_available, require_package

from ..utils import TeleopEvents
from .gamepad_report_descriptors import (
    DUNEFOX_HID_REPORT_DESCRIPTOR,
    HID_REPORT_DESCRIPTORS,
    LOGITECH_HID_REPORT_DESCRIPTOR,
    LOGITECH_PYGAME_REPORT_DESCRIPTOR,
    PYGAME_REPORT_DESCRIPTORS,
    GamepadActionMapping,
    GamepadMotionMapping,
    HIDAxisBinding,
    HIDButtonBinding,
    HIDDpadBinding,
    HIDGamepadReportDescriptor,
    ParsedGamepadReport,
    PygameAxisBinding,
    PygameGamepadReportDescriptor,
    episode_status_from_button,
    episode_status_from_buttons,
    get_hid_report_descriptor,
    get_pygame_report_descriptor,
    parse_hid_gamepad_report,
    read_pygame_gamepad_state,
)

__all__ = [
    "DUNEFOX_HID_REPORT_DESCRIPTOR",
    "HID_REPORT_DESCRIPTORS",
    "LOGITECH_HID_REPORT_DESCRIPTOR",
    "LOGITECH_PYGAME_REPORT_DESCRIPTOR",
    "PYGAME_REPORT_DESCRIPTORS",
    "GamepadActionMapping",
    "GamepadController",
    "GamepadControllerHID",
    "GamepadMotionMapping",
    "HIDAxisBinding",
    "HIDButtonBinding",
    "HIDDpadBinding",
    "HIDGamepadReportDescriptor",
    "InputController",
    "KeyboardController",
    "ParsedGamepadReport",
    "PygameAxisBinding",
    "PygameGamepadReportDescriptor",
    "episode_status_from_button",
    "episode_status_from_buttons",
    "get_hid_report_descriptor",
    "get_pygame_report_descriptor",
    "parse_hid_gamepad_report",
    "read_pygame_gamepad_state",
]

if TYPE_CHECKING or _pygame_available:
    import pygame
else:
    pygame = None  # type: ignore[assignment]

if TYPE_CHECKING or _hidapi_available:
    import hid
else:
    hid = None  # type: ignore[assignment]


class InputController:
    """Base class for input controllers that generate motion deltas."""

    def __init__(self, x_step_size=1.0, y_step_size=1.0, z_step_size=1.0):
        """
        Initialize the controller.

        Args:
            x_step_size: Base movement step size in meters
            y_step_size: Base movement step size in meters
            z_step_size: Base movement step size in meters
        """
        self.x_step_size = x_step_size
        self.y_step_size = y_step_size
        self.z_step_size = z_step_size
        self.running = True
        self.episode_end_status = None  # None, "success", or "failure"
        self.intervention_flag = False
        self.open_gripper_command = False
        self.close_gripper_command = False

    def start(self):
        """Start the controller and initialize resources."""
        pass

    def stop(self):
        """Stop the controller and release resources."""
        pass

    def get_deltas(self):
        """Get the current movement deltas (dx, dy, dz) in meters."""
        return 0.0, 0.0, 0.0

    def update(self):
        """Update controller state - call this once per frame."""
        pass

    def __enter__(self):
        """Support for use in 'with' statements."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure resources are released when exiting 'with' block."""
        self.stop()

    def get_episode_end_status(self):
        """
        Get the current episode end status.

        Returns:
            None if episode should continue, "success" or "failure" otherwise
        """
        status = self.episode_end_status
        self.episode_end_status = None  # Reset after reading
        return status

    def should_intervene(self):
        """Return True if intervention flag was set."""
        return self.intervention_flag

    def gripper_command(self):
        """Return the current gripper command."""
        if self.open_gripper_command == self.close_gripper_command:
            return "stay"
        elif self.open_gripper_command:
            return "open"
        elif self.close_gripper_command:
            return "close"


class KeyboardController(InputController):
    """Generate motion deltas from keyboard input."""

    def __init__(self, x_step_size=1.0, y_step_size=1.0, z_step_size=1.0):
        super().__init__(x_step_size, y_step_size, z_step_size)
        self.key_states = {
            "forward_x": False,
            "backward_x": False,
            "forward_y": False,
            "backward_y": False,
            "forward_z": False,
            "backward_z": False,
            "quit": False,
            "success": False,
            "failure": False,
        }
        self.listener = None

    def start(self):
        """Start the keyboard listener."""
        from pynput import keyboard

        def on_press(key):
            try:
                if key == keyboard.Key.up:
                    self.key_states["forward_x"] = True
                elif key == keyboard.Key.down:
                    self.key_states["backward_x"] = True
                elif key == keyboard.Key.left:
                    self.key_states["forward_y"] = True
                elif key == keyboard.Key.right:
                    self.key_states["backward_y"] = True
                elif key == keyboard.Key.shift:
                    self.key_states["backward_z"] = True
                elif key == keyboard.Key.shift_r:
                    self.key_states["forward_z"] = True
                elif key == keyboard.Key.esc:
                    self.key_states["quit"] = True
                    self.running = False
                    return False
                elif key == keyboard.Key.enter:
                    self.key_states["success"] = True
                    self.episode_end_status = TeleopEvents.SUCCESS
                elif key == keyboard.Key.backspace:
                    self.key_states["failure"] = True
                    self.episode_end_status = TeleopEvents.FAILURE
            except AttributeError:
                pass

        def on_release(key):
            try:
                if key == keyboard.Key.up:
                    self.key_states["forward_x"] = False
                elif key == keyboard.Key.down:
                    self.key_states["backward_x"] = False
                elif key == keyboard.Key.left:
                    self.key_states["forward_y"] = False
                elif key == keyboard.Key.right:
                    self.key_states["backward_y"] = False
                elif key == keyboard.Key.shift:
                    self.key_states["backward_z"] = False
                elif key == keyboard.Key.shift_r:
                    self.key_states["forward_z"] = False
                elif key == keyboard.Key.enter:
                    self.key_states["success"] = False
                elif key == keyboard.Key.backspace:
                    self.key_states["failure"] = False
            except AttributeError:
                pass

        self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.listener.start()

        print("Keyboard controls:")
        print("  Arrow keys: Move in X-Y plane")
        print("  Shift and Shift_R: Move in Z axis")
        print("  Enter: End episode with SUCCESS")
        print("  Backspace: End episode with FAILURE")
        print("  ESC: Exit")

    def stop(self):
        """Stop the keyboard listener."""
        if self.listener and self.listener.is_alive():
            self.listener.stop()

    def get_deltas(self):
        """Get the current movement deltas from keyboard state."""
        delta_x = delta_y = delta_z = 0.0

        if self.key_states["forward_x"]:
            delta_x += self.x_step_size
        if self.key_states["backward_x"]:
            delta_x -= self.x_step_size
        if self.key_states["forward_y"]:
            delta_y += self.y_step_size
        if self.key_states["backward_y"]:
            delta_y -= self.y_step_size
        if self.key_states["forward_z"]:
            delta_z += self.z_step_size
        if self.key_states["backward_z"]:
            delta_z -= self.z_step_size

        return delta_x, delta_y, delta_z


class GamepadController(InputController):
    """Generate motion deltas from gamepad input."""

    def __init__(
        self,
        x_step_size=1.0,
        y_step_size=1.0,
        z_step_size=1.0,
        deadzone=0.1,
        report_descriptor: PygameGamepadReportDescriptor | None = None,
    ):
        require_package("pygame", extra="gamepad")
        super().__init__(x_step_size, y_step_size, z_step_size)
        self.deadzone = deadzone
        self.report_descriptor = report_descriptor or LOGITECH_PYGAME_REPORT_DESCRIPTOR
        self.joystick = None
        self.intervention_flag = False
        self.axes = {name: 0.0 for name in self.report_descriptor.axes}
        self.buttons = {name: False for name in self.report_descriptor.buttons}

    def start(self):
        """Initialize pygame and the gamepad."""
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            logging.error("No gamepad detected. Please connect a gamepad and try again.")
            self.running = False
            return

        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        logging.info(
            f"Initialized gamepad: {self.joystick.get_name()} "
            f"with {self.report_descriptor.name} descriptor"
        )

        print("Gamepad controls:")
        print("  Left analog stick: Move in X-Y plane")
        print("  Right analog stick (vertical): Move in Z axis")
        print("  B/Circle button: Exit")
        print("  Y/Triangle button: End episode with SUCCESS")
        print("  A/Cross button: End episode with FAILURE")
        print("  X/Square button: Rerecord episode")

    def stop(self):
        """Clean up pygame resources."""
        if pygame.joystick.get_init():
            if self.joystick:
                self.joystick.quit()
            pygame.joystick.quit()
        pygame.quit()

    def update(self):
        """Process pygame events to get fresh gamepad readings."""
        if self.joystick is None:
            return

        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                button_name = self.report_descriptor.button_name(event.button)
                episode_status = episode_status_from_button(button_name, self.report_descriptor.actions)
                if episode_status is not None:
                    self.episode_end_status = episode_status

            # Reset episode status on button release
            elif event.type == pygame.JOYBUTTONUP:
                button_name = self.report_descriptor.button_name(event.button)
                if episode_status_from_button(button_name, self.report_descriptor.actions) is not None:
                    self.episode_end_status = None

        try:
            parsed_report = read_pygame_gamepad_state(self.joystick, self.report_descriptor, self.deadzone)
            self.axes = parsed_report.axes
            self.buttons = parsed_report.buttons
            actions = self.report_descriptor.actions
            self.intervention_flag = self.buttons.get(actions.intervention, False)
            self.open_gripper_command = self.buttons.get(actions.open_gripper, False)
            self.close_gripper_command = self.buttons.get(actions.close_gripper, False)
        except pygame.error:
            logging.error("Error reading gamepad. Is it still connected?")

    def get_deltas(self):
        """Get the current movement deltas from gamepad state."""
        return self.report_descriptor.motion.get_deltas(
            self.axes,
            self.x_step_size,
            self.y_step_size,
            self.z_step_size,
        )


class GamepadControllerHID(InputController):
    """Generate motion deltas from gamepad input using HIDAPI."""

    def __init__(
        self,
        x_step_size=1.0,
        y_step_size=1.0,
        z_step_size=1.0,
        deadzone=0.1,
        report_descriptor: HIDGamepadReportDescriptor | None = None,
    ):
        """
        Initialize the HID gamepad controller.

        Args:
            step_size: Base movement step size in meters
            z_scale: Scaling factor for Z-axis movement
            deadzone: Joystick deadzone to prevent drift
        """
        require_package("hidapi", extra="gamepad", import_name="hid")
        super().__init__(x_step_size, y_step_size, z_step_size)
        self.deadzone = deadzone
        self.report_descriptor = report_descriptor or LOGITECH_HID_REPORT_DESCRIPTOR
        self.device = None
        self.device_info = None

        # Movement values (normalized from -1.0 to 1.0)
        self.left_x = 0.0
        self.left_y = 0.0
        self.right_x = 0.0
        self.right_y = 0.0

        # Button states
        self.axes = {name: 0.0 for name in self.report_descriptor.axes}
        self.buttons = {name: False for name in self.report_descriptor.buttons}

    def find_device(self):
        """Look for the gamepad device by vendor and product ID."""
        devices = hid.enumerate()
        for device in devices:
            if self.report_descriptor.matches_device(device):
                return device

        logging.error(
            f"No gamepad found for {self.report_descriptor.name}, check the connection and descriptor"
        )
        return None

    def start(self):
        """Connect to the gamepad using HIDAPI."""
        self.device_info = self.find_device()
        if not self.device_info:
            self.running = False
            return

        try:
            logging.info(f"Connecting to gamepad at path: {self.device_info['path']}")
            self.device = hid.device()
            self.device.open_path(self.device_info["path"])
            self.device.set_nonblocking(1)

            manufacturer = self.device.get_manufacturer_string()
            product = self.device.get_product_string()
            logging.info(
                f"Connected to {manufacturer} {product} "
                f"with {self.report_descriptor.name} descriptor"
            )

            logging.info("Gamepad controls (HID mode):")
            logging.info("  Left analog stick: Move in X-Y plane")
            logging.info("  Right analog stick: Move in Z axis (vertical)")
            logging.info("  Button 1/B/Circle: Exit")
            logging.info("  Button 2/A/Cross: End episode with SUCCESS")
            logging.info("  Button 3/X/Square: End episode with FAILURE")

        except OSError as e:
            logging.error(f"Error opening gamepad: {e}")
            logging.error("You might need to run this with sudo/admin privileges on some systems")
            self.running = False

    def stop(self):
        """Close the HID device connection."""
        if self.device:
            self.device.close()
            self.device = None

    def update(self):
        """
        Read and process the latest gamepad data.
        Due to an issue with the HIDAPI, we need to read the read the device several times in order to get a stable reading
        """
        for _ in range(10):
            self._update()

    def _update(self):
        """Read and process the latest gamepad data."""
        if not self.device or not self.running:
            return

        try:
            # Read data from the gamepad
            data = self.device.read(64)
            parsed_report = parse_hid_gamepad_report(data, self.report_descriptor, self.deadzone)
            if parsed_report is None:
                return

            self.axes = parsed_report.axes
            self.buttons = parsed_report.buttons

            self.left_x = self.axes.get("left_x", 0.0)
            self.left_y = self.axes.get("left_y", 0.0)
            self.right_x = self.axes.get("right_x", 0.0)
            self.right_y = self.axes.get("right_y", 0.0)

            actions = self.report_descriptor.actions
            self.intervention_flag = self.buttons.get(actions.intervention, False)
            self.open_gripper_command = self.buttons.get(actions.open_gripper, False)
            self.close_gripper_command = self.buttons.get(actions.close_gripper, False)
            self.episode_end_status = episode_status_from_buttons(self.buttons, actions)

        except OSError as e:
            logging.error(f"Error reading from gamepad: {e}")

    def get_deltas(self):
        """Get the current movement deltas from gamepad state."""
        return self.report_descriptor.motion.get_deltas(
            self.axes,
            self.x_step_size,
            self.y_step_size,
            self.z_step_size,
        )
