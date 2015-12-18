#!/usr/bin/python3

import sys
import os
import argparse

import bnc

if hasattr(os, 'geteuid') and os.getuid() == 0:
    sys.exit("pyBNC can't run as root mate")

parser = argparse.ArgumentParser(description = "pyBNC IRC bouncer - for all your pythonic IRC needs.")
parser.add_argument("config_file", metavar = "<config-file>", help = "json config file", nargs="?")
parser.add_argument("-d", "--debug", help = "run in debug mode, don't fork(), log everything to stdout / stderr", action = "store_true")
parser.add_argument("-o", "--output", metavar = "output.log", help = "log file to write to, default is pybnc.log", default = "pybnc.log")
parser.add_argument("-p", "--pidfile", metavar = "pidfile.pid", help = "file to write pid to, default is pybnc.pid", default = "pybnc.pid")
args = parser.parse_args()
    
if args.config_file:
    config_file = args.config_file
else:
    # default json config file
    config_file = "config.json"

# don't fork if we're in debug mode
if args.debug:
    child = 0
else:
    child = os.fork()

if child == 0:
    bnc.run(config_file, debug = args.debug, log_to = args.output)
else:
    # write PID to pidfile
    try:
        f = open(args.pidfile, 'w')
        f.write("%s" % child)
    except:
        sys.stderr.write("can't write PID to %s" % args.pidfile)
    