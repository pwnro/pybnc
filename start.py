import sys, os, json
from pprint import pprint
from bouncer import Bouncer

if hasattr(os, 'geteuid') and os.getuid() == 0:
    sys.exit("can't run as root srry")

if sys.version_info < (3, 3):
    sys.exit("requires python 3.3 or later bra")

try:
    with open('config.json') as cfg_file:
        cfg = json.load(cfg_file)
except:
    sys.exit("can't read config file config.json")

if 'port' in cfg and 'bouncers' in cfg and len('bounceers') > 0:
    # start bouncer server - listen for connections and map them to the bncs
    
    for bcfg in cfg['bouncers']:
        print("bouncer %s: %s @ %s:%d - %s" % \
        ( bcfg['id'], bcfg['nick'], bcfg['server'], bcfg['port'], ', '.join(bcfg['channels']) ))
        
        b = Bouncer(bcfg)
        
        pprint(b.get_config())
else:
    sys.exit("no bouncers found in config file")
    
