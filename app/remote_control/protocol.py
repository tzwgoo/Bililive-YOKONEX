from __future__ import annotations


COMMAND_IDS = tuple(f"command_{name}" for name in (
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
))

ALLOWED_ACTIONS = {
    "command.send",
    "waveform.play",
    "waveform.stop",
    "output.fixed",
    "device.disconnect",
}
