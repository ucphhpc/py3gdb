#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# breakpoint - Python GDB breakpoint
# Copyright (C) 2019-2024  The pygdb Project lead by Brian Vinter
#
# This file is part of pygdb.
#
# pygdb is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# pygdb is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Python GNU debugger (GDB) breakpoint
https://devguide.python.org/gdb/
https://wiki.python.org/moin/DebuggingWithGdb
https://sourceware.org/gdb/onlinedocs/gdb/Python-API.html

USAGE:
import pygdb.breakpoint
pygdb.breakpoint.enable()
pygdb.breakpoint.set()

This will block the executing thread (at the pygdb.breakpoint.set() call)
until 'pygdb.console.extension.console_connected' is called
from the GDB console.
"""

import os
import sys
import logging
import signal
import time
import threading
import _pygdb

enabled = False
gdb_logger = None
console_connected = None
breakpoint_lock = threading.Lock()


def handle_sigcont(signalNumber, frame):
    """ NOTE: We do not forward SIGCONT because: 
    You can set a handler, but SIGCONT always makes the process continue regardless:
    https://www.gnu.org/software/libc/manual/html_node/Job-Control-Signals.html 
    """
    global console_connected
    breakpoint_lock.acquire()
    if not console_connected:
        console_connected = True
        log("GDB console attached")
    breakpoint_lock.release()


def enable(logger=None):
    """Enable breakpoint"""
    global enabled
    global console_connected
    global breakpoint_lock

    breakpoint_lock.acquire()
    if not enabled:
        enabled = True
        console_connected = False
        set_logger(logger)
        signal.signal(signal.SIGCONT, handle_sigcont)
        log("enabled")
    breakpoint_lock.release()


def log(msg):
    """log info messages"""
    if not enabled:
        return

    pid = os.getpid()
    tid = threading.current_thread().ident
    log_msg = "pygdb: (PID: %d, TID: 0x%0.x): %s" \
        % (pid, tid, msg)

    if isinstance(gdb_logger, logging.Logger):
        gdb_logger.info(log_msg)
    else:
        sys.stderr.write("pygdb: %s\n" % log_msg)


def set_logger(logger):
    """set logger to used by the log function"""
    if not enabled:
        return False

    global gdb_logger

    result = False
    if isinstance(logger, logging.Logger):
        gdb_logger = logger
        result = True

    return result


def set(logger=None):
    """Used to set breakpoint, busy-wait until gdb console is connected"""
    if not enabled:
        return

    global console_connected

    # Wait for gdb console
    breakpoint_lock.acquire()
    if logger is not None:
        set_logger(logger)
    while not console_connected:
        log("breakpoint.set: waiting for gdb console")
        breakpoint_lock.release()
        time.sleep(1)
        breakpoint_lock.acquire()
    breakpoint_lock.release()
    _pygdb.breakpoint_mark()
