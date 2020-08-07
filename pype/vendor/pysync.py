#!/usr/local/bin/python3
# https://github.com/snullp/pySync/blob/master/pySync.py

import sys
import shutil
import os
import time
import configparser
from os.path import (
    getsize,
    getmtime,
    isfile,
    isdir,
    join,
    abspath,
    expanduser,
    realpath
)
import logging

log = logging.getLogger(__name__)

ignoreFiles = ("Thumbs.db", ".DS_Store")

# this feature is not yet implemented
ignorePaths = []

if os.name == 'nt':
    # msvcrt can't function correctly in IDLE
    if 'idlelib.run' in sys.modules:
        print("Please don't run this script in IDLE.")
        sys.exit(0)
    import msvcrt

    def flush_input(str, set=None):
        if not set:
            while msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch == '\xff':
                    print("msvcrt is broken, this is weird.")
                    sys.exit(0)
            return input(str)
        else:
            return set
else:
    import select

    def flush_input(str, set=None):
        if not set:
            while len(select.select([sys.stdin.fileno()], [], [], 0.0)[0]) > 0:
                os.read(sys.stdin.fileno(), 4096)
            return input(str)
        else:
            return set


def compare(fa, fb, options_input=[]):
    if isfile(fa) == isfile(fb):
        if isdir(fa):
            walktree(fa, fb, options_input)
        elif isfile(fa):
            if getsize(fa) != getsize(fb) \
                    or int(getmtime(fa)) != int(getmtime(fb)):
                log.info(str((fa, ': size=', getsize(fa), 'mtime=',
                              time.asctime(time.localtime(getmtime(fa))))))
                log.info(str((fb, ': size=', getsize(fb), 'mtime=',
                              time.asctime(time.localtime(getmtime(fb))))))
                if getmtime(fa) > getmtime(fb):
                    act = '>'
                else:
                    act = '<'

                set = [i for i in options_input if i in [">", "<"]][0]

                s = flush_input('What to do?(>,<,r,n)[' + act + ']', set=set)
                if len(s) > 0:
                    act = s[0]
                if act == '>':
                    shutil.copy2(fa, fb)
                elif act == '<':
                    shutil.copy2(fb, fa)
                elif act == 'r':
                    if isdir(fa):
                        shutil.rmtree(fa)
                    elif isfile(fa):
                        os.remove(fa)
                    else:
                        log.info(str(('Remove: Skipping', fa)))
                    if isdir(fb):
                        shutil.rmtree(fb)
                    elif isfile(fb):
                        os.remove(fb)
                    else:
                        log.info(str(('Remove: Skipping', fb)))

        else:
            log.debug(str(('Compare: Skipping non-dir and non-file', fa)))
    else:
        log.error(str(('Error:', fa, ',', fb, 'have different file type')))


def copy(fa, fb, options_input=[]):
    set = [i for i in options_input if i in ["y"]][0]
    s = flush_input('Copy ' + fa + ' to another side?(r,y,n)[y]', set=set)
    if len(s) > 0:
        act = s[0]
    else:
        act = 'y'
    if act == 'y':
        if isdir(fa):
            shutil.copytree(fa, fb)
        elif isfile(fa):
            shutil.copy2(fa, fb)
        else:
            log.debug(str(('Copy: Skipping ', fa)))
    elif act == 'r':
        if isdir(fa):
            shutil.rmtree(fa)
        elif isfile(fa):
            os.remove(fa)
        else:
            log.debug(str(('Remove: Skipping ', fa)))


stoentry = []
tarentry = []


def walktree(source, target, options_input=[]):
    srclist = os.listdir(source)
    tarlist = os.listdir(target)
    if '!sync' in srclist:
        return
    if '!sync' in tarlist:
        return
    # files in source dir...
    for f in srclist:
        if f in ignoreFiles:
            continue
        spath = join(source, f)
        tpath = join(target, f)
        if spath in ignorePaths:
            continue
        if spath in stoentry:
            # just in case target also have this one
            if f in tarlist:
                del tarlist[tarlist.index(f)]
            continue

        # if also exists in target dir
        if f in tarlist:
            del tarlist[tarlist.index(f)]
            compare(spath, tpath, options_input)

        # exists in source dir only
        else:
            copy(spath, tpath, options_input)

    # exists in target dir only
    set = [i for i in options_input if i in ["<"]]

    for f in tarlist:
        if f in ignoreFiles:
            continue
        spath = join(source, f)
        tpath = join(target, f)
        if tpath in ignorePaths:
            continue
        if tpath in tarentry:
            continue
        if set:
            copy(tpath, spath, options_input)
        else:
            print("REMOVING: {}".format(f))
            if os.path.isdir(tpath):
                shutil.rmtree(tpath)
            else:
                os.remove(tpath)
            print("REMOVING: {}".format(f))


if __name__ == '__main__':
    stoconf = configparser.RawConfigParser()
    tarconf = configparser.RawConfigParser()
    stoconf.read("pySync.ini")
    tarconf.read(expanduser("~/.pysync"))
    stoname = stoconf.sections()[0]
    tarname = tarconf.sections()[0]

    # calculate storage's base folder
    if stoconf.has_option(stoname, 'BASE'):
        stobase = abspath(stoconf.get(stoname, 'BASE'))
        stoconf.remove_option(stoname, 'BASE')
    else:
        stobase = os.getcwd()

    # same, for target's base folder
    if tarconf.has_option(tarname, 'BASE'):
        tarbase = abspath(tarconf.get(tarname, 'BASE'))
        tarconf.remove_option(tarname, 'BASE')
    else:
        tarbase = expanduser('~/')

    print("Syncing between", stoname, "and", tarname)
    sto_content = {x: realpath(join(stobase, stoconf.get(stoname, x)))
                   for x in stoconf.options(stoname)}
    tar_content = {x: realpath(join(tarbase, tarconf.get(tarname, x)))
                   for x in tarconf.options(tarname)}
    stoentry = [sto_content[x] for x in sto_content]
    tarentry = [tar_content[x] for x in tar_content]

    for folder in sto_content:
        if folder in tar_content:
            print('Processing', folder)
            walktree(sto_content[folder], tar_content[folder], options_input)
    print("Done.")
