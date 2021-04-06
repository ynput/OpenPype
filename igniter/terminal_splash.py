# -*- coding: utf-8 -*-
"""OpenPype terminal animation."""
import blessed
from pathlib import Path
from time import sleep

NO_TERMINAL = False

try:
    term = blessed.Terminal()
except AttributeError:
    # this happens when blessed cannot find proper terminal.
    # If so, skip printing ascii art animation.
    NO_TERMINAL = True


def play_animation():
    """Play ASCII art OpenPype animation."""
    if NO_TERMINAL:
        return
    print(term.home + term.clear)
    frame_size = 7
    splash_file = Path(__file__).parent / "splash.txt"
    with splash_file.open("r") as sf:
        animation = sf.readlines()

    animation_length = int(len(animation) / frame_size)
    current_frame = 0
    for _ in range(animation_length):
        frame = "".join(
            scanline
            for y, scanline in enumerate(
                animation[current_frame : current_frame + frame_size]
            )
        )

        with term.location(0, 0):
            # term.aquamarine3_bold(frame)
            print(f"{term.bold}{term.aquamarine3}{frame}{term.normal}")

        sleep(0.02)
        current_frame += frame_size
    print(term.move_y(7))
