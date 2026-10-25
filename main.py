#!/usr/bin/env python3
# vim:set et sts=4 sw=4:
#
# ibus-googlepinyin - The GooglePinyin engine for IBus
#
# Copyright(c) 2011 Jiahua Huang <jhuangjiahua@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA.  

import os
import sys
import getopt
import gi
gi.require_version('IBus', '1.0')
from gi.repository import GLib, IBus
import factory

class IMApp:
    def __init__(self, exec_by_ibus):
        self.__mainloop = GLib.MainLoop()
        self.__bus = IBus.Bus.new()
        self.__bus.connect("destroy", self.__bus_destroy_cb)
        self.__factory = factory.EngineFactory(self.__bus)
        if exec_by_ibus:
            self.__bus.request_name("org.freedesktop.IBus.GooglePinyin", 0)
        else:
            self.__component = IBus.Component.new(
                "org.freedesktop.IBus.GooglePinyin", "GooglePinyin Component",
                "0.42.0", "GPL", "Jiahua Huang <jhuangjiahua@gmail.com>",
                "", "en")
            self.__component.add_engine(IBus.EngineDesc.new(
                "googlepinyin", "GooglePinyin", "GooglePinyin Input Method",
                "zh_CN", "GPL", "Jiahua Huang <jhuangjiahua@gmail.com>",
                os.path.join(os.path.dirname(__file__), "icons", "ibus-googlepinyin.png"), "default"))
            self.__bus.register_component(self.__component)

    def run(self):
        self.__mainloop.run()

    def __bus_destroy_cb(self, bus):
        self.__mainloop.quit()


def launch_engine(exec_by_ibus):
    IMApp(exec_by_ibus).run()

def print_help(out, v = 0):
    print("-i, --ibus             execute by ibus.", file=out)
    print("-h, --help             show this message.", file=out)
    print("-d, --daemonize        daemonize ibus", file=out)
    sys.exit(v)

def main():
    daemonize = False
    exec_by_ibus = False
    shortopt = "hdi"
    longopt = ["help", "daemonize", "ibus"]
    try:
        opts, args = getopt.getopt(sys.argv[1:], shortopt, longopt)
    except getopt.GetoptError as err:
        print_help(sys.stderr, 1)

    for o, a in opts:
        if o in("-h", "--help"):
            print_help(sys.stdout)
        elif o in ("-d", "--daemonize"):
            daemonize = True
        elif o in ("-i", "--ibus"):
            exec_by_ibus = True
        else:
            print("Unknown argument: %s" % o, file=sys.stderr)
            print_help(sys.stderr, 1)

    if daemonize:
        if os.fork():
            sys.exit()

    launch_engine(exec_by_ibus)

if __name__ == "__main__":
    main()
