import sys, os, json
from pprint import pprint
from my_irc import IrcClient
from bnc_server import BncServer
from bnc_client import BncClient

import select
#import time, thread

if hasattr(os, 'geteuid') and os.getuid() == 0:
    sys.exit("can't run as root srry")

#if sys.version_info < (3, 3):
#    sys.exit("requires python 3.3 or later bra")

try:
    with open('config.json') as cfg_file:
        cfg = json.load(cfg_file)
except:
    sys.exit("can't read config file config.json")

bouncers = []
bouncer_sockets = []
bnc_clients = []

if 'bouncers' in cfg and len(cfg['bouncers']) > 0:
    # start bouncer server - listen for connections and map them to the bncs
    bcfgs = cfg['bouncers']
    
    for bcfg in bcfgs:
        print("bouncer %s: %s @ %s:%d - %s" % \
        ( bcfg['id'], bcfg['nick'], bcfg['server'], bcfg['port'], ', '.join(bcfg['channels']) ))
        
        # connect to irc server
        b = IrcClient(bcfg)
        b.connect()
        
        if b.sock != False:
            print("bouncer %s connected, putting socket on the select() list" % bcfg['id'])
            bouncers.append(b)
            bouncer_sockets.append(b.sock)
        else:
            print("bouncer %s can not connect.." % bcfg['id'])
else:
    sys.exit("no bouncers found in config file")    
    
if len(bouncer_sockets) == 0:
    sys.exit("no bouncer sockets could be created, existing..")
    
is_readable = list(bouncer_sockets)
is_writable = list(bouncer_sockets)
is_error = []    
    
# launch server
server = False
if 'server' in cfg:
    server_cfg = cfg['server']
    
    server = BncServer(server_cfg)
    
    if server.sock != False:
        is_readable.append(server.sock)
        is_writable.append(server.sock)
    else:
        sys.exit("server can't start, shutting down..")
    
# main select() loop
while True :
    try:
        sel_read, sel_write, sel_error = select.select(is_readable, is_writable, is_error)
        
        for sock in sel_error:
            # remove from lists
            print("select() error detected")
            try:
                is_readable.remove(sock)
                is_writable.remove(sock)
            except:
                pass
        
        for sock in sel_read:
            # incoming message from ircd on one of the bouncers?
            if sock in bouncer_sockets:
                bouncer = False
                for b in bouncers:
                    if sock == b.sock:
                        bouncer = b
                        break
                
                if bouncer == False:
                    print("could not find bouncer for socket, closing it..")
                    sock.close()
                    break
                   
                received = sock.recv(2048)
                
                bouncer_id = bouncer.config['id']
                
                if not received:
                    print(bouncer_id + ": disconnected from server")
                    
                    try:
                        is_readable.remove(sock)
                    except:
                        pass
                    
                    sock.close()
                    # ar trebui scoasa din is_readable, is_writable
                else:
                    # primim bytes -> decode in utf8
                    lines = received.decode('utf-8')
                    
                    lines = lines.split("\n")
                    lines = list(map(lambda l: l.strip(), lines))
                    lines = filter(None, lines)
                    
                    for line in lines:
                        #print(bouncer_id + ": " + line)
                        bouncer.parse(line.strip())
                        
                        
            elif sock == server.sock:
                # new connection on server socket
                client, address = server.sock.accept()
                print("server - new connection %d from %s" % (client.fileno(), address))
                
                # add client socket to sel_read and sel_write lists
                is_readable.append(client)
                is_writable.append(client)
            
            else:
                # one of the bnc clients
                received = sock.recv(2048)
                
                if not received:
                    print("bnc client disconnected")
                    
                    # remove from is_readable
                    try:
                        is_readable.remove(sock)
                        is_writable.remove(sock)
                    except:
                        pass
                    
                    sock.close()
                else:
                    #lines = received.encode('utf-8').split("\n")
                    lines = received.decode('utf-8').split("\n")
                    
                    for line in lines:
                        print(line.strip())
                        words = line.split(' ')
                        words_len = len(words)
                        
                        if words_len > 1 and words[0] == 'USER':
                            client_id = words[1]
                            
                            # check if we have a bouncer up for this id
                            for bnc in bouncers:
                                if hasattr(bnc, 'id') and bnc.id == client_id:
                                    print("client connected to bouncer %s" % client_id)
                                    break
                                else:
                                    bnc = False
                                    
                            if bnc == False:
                                print("no bouncer with id %s found for client" % client_id)
                            else:
                                # connect client to bouncer
                                print("connecting client to bouncer")
                                bnc.client_connected = True
                                bnc.client_sockets.append(sock)
                                
                                # sending la misto errnoues nickname
                                sock.send(bytes(':irc.rizon.no 433 * zzzzz :Nickname is already in use.', 'UTF-8'))
                                
        for sock in sel_write:
            pass
            
    except KeyboardInterrupt:
        print('got interrupt, closing sockets')
        
        for sock in bouncer_sockets:
            sock.close()
        break    
        
    
