# -*- coding: utf-8 -*-
"""Provide profiling decorator."""
import os
import cProfile


def do_profile(fn, to_file=None):
    """Wraps function in profiler run and print stat after it is done.

    Args:
        to_file (str, optional): If specified, dumps stats into the file
        instead of printing.

    """
    if to_file:
        to_file = to_file.format(pid=os.getpid())

    def profiled(*args, **kwargs):
        profiler = cProfile.Profile()
        try:
            profiler.enable()
            res = fn(*args, **kwargs)
            profiler.disable()
            return res
        finally:
            if to_file:
                profiler.dump_stats(to_file)
            else:
                profiler.print_stats()
