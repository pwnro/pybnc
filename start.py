import sys, os, json
from pprint import pprint
from bouncer import Bouncer

import time, thread

if hasattr(os, 'geteuid') and os.getuid() == 0:
    sys.exit("can't run as root srry")

#if sys.version_info < (3, 3):
#    sys.exit("requires python 3.3 or later bra")

try:
    with open('config.json') as cfg_file:
        cfg = json.load(cfg_file)
except:
    sys.exit("can't read config file config.json")

if 'bouncers' in cfg and len('bouncers') > 0:
    # start bouncer server - listen for connections and map them to the bncs
    
    for bcfg in cfg['bouncers']:
        print("bouncer %s: %s @ %s:%d - %s" % \
        ( bcfg['id'], bcfg['nick'], bcfg['server'], bcfg['port'], ', '.join(bcfg['channels']) ))
        
        # start bouncer thread
        b = Bouncer(bcfg)
        
        b.connect()
        if b.registered:
            print("bouncer %s registered.." % bcfg['id'])
        else:
            print("bouncer %s can not register.." % bcfg['id'])
            
    c = raw_input("type something to quit")
        
else:
    sys.exit("no bouncers found in config file")
    
