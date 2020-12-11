# -*- coding: utf-8 -*-
"""Pype terminal animation :)"""
import os
from pathlib import Path
from time import sleep
import sys


def play_animation():
    frame_size = 7
    splash_file = Path(__file__).parent / "splash.txt"
    with splash_file.open("r") as sf:
        animation = sf.readlines()

    animation_length = int(len(animation) / frame_size)
    current_frame = 0
    for frame in range(animation_length):
        if sys.platform.startswith('win'):
            os.system('cls')
        else:
            os.system('clear')
        for scanline in animation[current_frame:current_frame + frame_size]:
            print(scanline.rstrip())
        sleep(0.05)
        current_frame += frame_size
