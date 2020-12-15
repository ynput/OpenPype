# -*- coding: utf-8 -*-
"""Pype terminal animation."""
import blessed
from pathlib import Path
from time import sleep


term = blessed.Terminal()


def play_animation():
    """Play ASCII art Pype animation."""
    print(term.home + term.clear)
    frame_size = 7
    splash_file = Path(__file__).parent / "splash.txt"
    with splash_file.open("r") as sf:
        animation = sf.readlines()

    animation_length = int(len(animation) / frame_size)
    current_frame = 0
    for _ in range(animation_length):
        frame = ""
        y = 0
        for scanline in animation[current_frame:current_frame + frame_size]:
            frame += scanline
            y += 1

        with term.location(0, 0):
            # term.aquamarine3_bold(frame)
            print(f"{term.bold}{term.aquamarine3}{frame}{term.normal}")

        sleep(0.02)
        current_frame += frame_size
    print(term.move_y(7))
