import sys
import socket
import os
import signal
import select
import json
import logging
import time

from hashlib import md5
from random import randint
from my_irc import MyIrc as mirc

BNC_DEBUG = False

# lists for select()
is_readable = []
is_writable = []
is_error = []

# irc connection bouncer
class Conn(object):
    port = 0
    sock = False
    
    # has the bouncer succesfully registered on the ircd?
    registered = False

    cfg = {}    
    client_sockets = []
    
    # if the bouncer should retry to connect to server all the time
    auto_connect = True
    
    # delay for retrying to connect to server, in seconds
    auto_connect_delay = 5
    
    real_server_name = ''
    nick = ''
    userhost = ''
    
    def send(self, line):
        return mirc.send(self.sock, line)
    
    def __init__(self, cfg):
        self.cfg = cfg
        
        self.real_server_name = cfg['server']
        self.nick = cfg['nick']
        
        logging.info("starting bouncer %s - %s @ %s" % (self.cfg['user'], self.cfg['nick'], self.cfg['server']))
        logging.debug(repr(self.cfg))
        
        self.sock = mirc.connect(self.cfg)
        
        if self.userhost == '':
            self.userhost = cfg['nick'] + '!~' + cfg['user'] + self.sock.getsockname()[0]

        signal.signal(signal.SIGINT, self.sighandler)
        
    def parse(self, line):
        words = line.split(' ')
        words_len = len(words)
        
        # welcome message /motd and irc command replies received start with ":"
        if words_len > 0 and words[0].startswith(':'):
            if words_len > 1 and words[1].isdigit():
                irc_code = words[1]
                self.reply_to_code(irc_code, line, words)
                
            # grab userhost from MODE reply on registering
            if self.registered and words_len > 1 and words[1] == 'MODE' and words[2] == self.nick:
                self.userhost = words[0][1:]
                
        # reply to PING
        if words[0].startswith('PING'):
            pong = words[1][1:]
            self.send("PONG :%s" % pong)
            
        if self.client_sockets != []:
            self.send_to_client_sockets(line)
            
    def send_to_client_sockets(self, data):
        if self.client_sockets != []:
            for c_sock in self.client_sockets:
                try:
                    mirc.send(c_sock, data)
                except:
                    logging.error("could not send data read from ircd to client")
                    # remove client_socket from list
                    self.client_sockets.remove(c_sock)
    
    def reply_to_code(self, code, line = False, words = False):
        if code == "433" and self.registered == False:
            # generate new nick and send it to ircd
            newnick = "%s%d" % (self.nick, randint(1, 100))
            self.send("NICK %s" % newnick)
            
        if code == "001" and self.registered == False:
            # registed on the network
            self.registered = True

            try:            
                self.real_server_name = words[0][1:]
                self.nick = words[2]
            except:
                # couldn't grab server name and nick from welcome message
                logging.warning("couldn't grab real server name and real nick from server welcome message")
                pass
            
            self.after_register()
        
    def sighandler(self, signum, frame):
        # close the server
        logging.info('received kb interrupt, shutting down bnc client socket')
        self.sock.close()
        
    def send_pybnc_message(self, client, message, code = "100"):
        mirc.send(client, ":pyBNC %s %s :%s" % (code, self.nick, message))
    
    # commands to run after the user has connected to a connected bouncer
    def setup_user(self, client):
        self.send_pybnc_message(client, "welcome to pyBNC", "001")
        self.send_pybnc_message(client, "running pyBNC version 1.3.37", "002")
        
        if self.registered:
            self.send_pybnc_message(client, "bouncer is connected to %s:%d (%s)" % (self.cfg['server'], self.cfg['port'], self.real_server_name))
        else:
            self.send_pybnc_message(client, "bouncer is not connected")
            self.send_pybnc_message(client, "bouncer configured for %s:%d (%s)" % (self.cfg['server'], self.cfg['port'], self.real_server_name))
            
            if self.auto_connect:
                self.send_pybnc_message(client, "auto reconnect enabled")
            else:
                self.send_pybnc_message(client, "auto reconnect disabled")
                
            self.send_pybnc_message(client, "type /bhelp for list of pyBNC commands")
        
        for channel in self.cfg['channels']:
            mirc.join(self.sock, channel)
            
            # emulate joining the channel in case we're already on the channel
            mirc.send(client, ':%s JOIN %s' % (self.userhost, channel))
            mirc.names(self.sock, channel)
            mirc.topic(self.sock, channel)
        
    # commands to run after the bouncer has connected to the irc network    
    def after_register(self):
        # join channels specified in config file
        for channel in self.cfg['channels']:
            mirc.join(self.sock, channel)
            
        # register to nickserv maybe?

# bouncer server
class Server(object):
    backlog = 10
    port = 0
    sock = False
    
    def __init__(self, cfg):
        self.cfg = cfg
        self.port = cfg['port']
        
        logging.info("starting server")
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', self.port))
        
        logging.info('listening on port %d' % self.port)
        self.sock.listen(self.backlog)
        
        logging.debug("server backlog = %d" % self.backlog)
        
        # Trap keyboard interrupts
        signal.signal(signal.SIGINT, self.sighandler)
        
    def sighandler(self, signum, frame):
        # close the server
        logging.info('received kb interrupt, shutting down server')
        self.sock.close()
        
def get_pybnc_help():
    help_dict = {
        'BQUIT <msg>': "disconnect bouncer from irc (with <msg>), turn auto-connect off",
        'BHELP': "see pyBNC commands and descriptions",
        'BSHUTDOWN': "shut down irc bouncer",
        'BCONFIG': "get pyBNC config",
        'BSET <key> <value>': "set config option <key> to <value>",
        'BAWAY <msg>': "set <msg> as away message - set on disconnecting from bouncer",
        'BAUTOCONNECT [1/0]': "set autoconnect on or off",
        'BCONNECT': "connect to ircd (only if not connected)",
        'BRECONNECT': "reconnect to ircd server"
    }
    
    return help_dict
        
def remove_socket(sock):
    global is_readable, is_writable
    
    try:
        is_readable.remove(sock)
        is_writable.remove(sock)
    except:
        pass

def add_socket(sock):
    global is_readable, is_writable
    
    try:
        is_readable.append(sock)
        is_writable.append(sock)
    except:
        pass
    
def md5hash(plaintext):
    m = md5()
    m.update(plaintext.encode('utf-8'))
    
    return m.hexdigest()

def run(infile, debug = False, log_to = 'pybnc.log'):
    global BNC_DEBUG
    BNC_DEBUG = debug
    
    # if debugging is on, log to stdout
    # else log to file
    if BNC_DEBUG:
        logging.debug("debugging enabled")
    else:
        try:
            logging.basicConfig(filename = log_to, level = logging.INFO)
        except:
            logging.error("can't write to logfile %s" % log_to)
    
    try:
        with open(infile) as cfg_file:
            cfg = json.load(cfg_file)
    except:
        logging.critical("can't read config file '%s'" % infile)
        sys.exit(1)
    
    if 'bouncer' not in cfg or 'server' not in cfg:
        logging.critical("invalid config file '%s'" % infile)
        sys.exit(1)

    server = Server(cfg['server'])
    if server.sock != False:
        add_socket(server.sock)
    else:
        logging.critical("server can't start, shutting down")
        sys.exit(1)
    
    def bouncer_try(bouncer_cfg):
        # fire up the bouncer
        bouncer = Conn(bouncer_cfg)
        if bouncer.sock != False:
            add_socket(bouncer.sock)
        else:
            logging.error("could not create bouncer socket")
            
        return bouncer
    
    bouncer = bouncer_try(cfg['bouncer'])
    
    # main select() loop
    while True:
        try:
            sel_read, sel_write, sel_error = select.select(is_readable, is_writable, is_error)
            
            for sock in sel_error:
                # remove from lists
                logging.error("select() error detected, removing sock")
                remove_socket(sock)
            
            for sock in sel_read:
                # incoming data from the ircd to the bouncer
                if sock == bouncer.sock:
                    lines = mirc.recv(sock)
                    
                    if not lines:
                        remove_socket(sock)
                        if bouncer.auto_connect:
                            logging.info("bouncer disconnected from server, attempting to reconnect in %d seconds" % bouncer.auto_connect_delay)
                            time.sleep(bouncer.auto_connect_delay)
                            bouncer = bouncer_try(cfg['bouncer'])
                        else:
                            logging.info("bouncer disconnected from server, auto connect disabled")
                        
                        continue
                    
                    # feed the bouncer cu ce zice ircdu
                    for line in lines:
                        # va trimite automat si catre clientul conectat la server, daca e conectat
                        logging.debug(line)
                        
                        #hooks.received_from_ircd(line)
                        bouncer.parse(line)
                            
                # conexiune noua pe server
                elif sock == server.sock:
                    client, address = server.sock.accept()
                    logging.info("new connection %s (%d)" % (address, client.fileno()))
                    
                    # add client socket to select() loop
                    add_socket(client)
                
                # de la unul din clientii conectati la server
                else:
                    lines = mirc.recv(sock)
                    
                    if not lines:
                        logging.info("client disconnected from server")
                        try:
                            bouncer.client_sockets.remove(sock)
                        except:
                            pass
                        
                        remove_socket(sock)
                        continue
                    
                    # parsam ce trimite clientul                    
                    for line in lines:
                        words = line.split(' ')
                        words_len = len(words)
                        
                        # autentificare
                        if sock not in bouncer.client_sockets:
                            authentified = False
                            
                            if words_len > 1 and words[0] == 'PASS':
                                password = words[1].strip()
                                
                                if md5hash(password) == cfg['server']['pass']:
                                    authentified = True
                                    bouncer.client_sockets.append(sock)
                                else:
                                    mirc.send(sock, ":pyBNC 100 pyBNC :wrong password, disconnecting")
                                    # wrong password, disconnect user
                                    remove_socket(sock)
                                    
                            elif words_len > 1 and words[0] == 'USER':
                                    mirc.send(sock, ":pyBNC 100 pyBNC :auth required, disconnecting")
                                    # no password, disconnect user
                                    remove_socket(sock)                            
                        else:
                            authentified = True                    
    
                            if words_len > 1 and words[0] == 'USER':
                                # send motd / greet, join channels
                                bouncer.setup_user(sock)
                                    
                            # intercept QUIT command from client
                            elif words_len > 0 and words[0] == 'QUIT':
                                logging.info("client disconnected, intercepting QUIT")
                                remove_socket(sock)
                                
                            # BHELP -> send pybnc help
                            elif words_len > 0 and words[0].upper() == "BHELP":
                                help_dict = get_pybnc_help()
                                
                                for cmd, desc in help_dict.items():
                                    bouncer.send_pybnc_message(sock, "%s => %s" % (cmd, desc))
                                    
                            # BCONNRESET -> forcefully disconnect bouncer from ircd, simulate conn reset
                            elif words_len > 0 and words[0].upper() == "BCONNRESET":
                                logging.info("close()ing bouncer irc connection")
                                bouncer.sock.close()
                                
                            # BCONFIG -> get config values
                            elif words_len > 0 and words[0].upper() == "BCONFIG":
                                bouncer.send_pybnc_message(sock, repr(bouncer.cfg))
                                
                            # BQUIT -> disconnect bouncer from irc (with optional message)
                            elif words_len > 0 and words[0].upper() == "BQUIT":
                                # disable auto reconnect
                                bouncer.auto_connect = False
                                
                                bouncer.send_pybnc_message(sock, "disconnecting from server %s (%s)" % (bouncer.cfg['server'], bouncer.real_server_name))
                                if words_len > 1:
                                    quit_message = words[1:]
                                    mirc.quit(bouncer.sock, quit_message)
                                else:
                                    mirc.quit(bouncer.sock)
                                    
                            # BSHUTDOWN -> shut down irc bouncer
                            elif words_len > 0 and words[0].upper() == "BSHUTDOWN":
                                bouncer.send_pybnc_message(sock, "shutting down irc bouncer")
                                bouncer.send_pybnc_message(sock, "disconnecting from server %s (%s)" % (bouncer.cfg['server'], bouncer.real_server_name))
                                if words_len > 1:
                                    quit_message = words[1:]
                                    mirc.quit(bouncer.sock, quit_message)
                                else:
                                    mirc.quit(bouncer.sock)
                                    
                                for s in is_readable:
                                    s.close()
                                    
                                sys.exit()
                                
                            # BSHUTDOWN -> shut down irc bouncer
                            elif words_len > 0 and words[0].upper() == "BSHUTDOWN":
                                bouncer.send_pybnc_message(sock, "shutting down irc bouncer")
                                bouncer.send_pybnc_message(sock, "disconnecting from server %s (%s)" % (bouncer.cfg['server'], bouncer.real_server_name))
                                if words_len > 1:
                                    quit_message = words[1:]
                                    mirc.quit(bouncer.sock, quit_message)
                                else:
                                    mirc.quit(bouncer.sock)
                                    
                                for s in is_readable:
                                    s.close()
                                    
                                sys.exit()                                
                                    
                            # send anything else to ircd through irc client
                            else:
                                mirc.send(bouncer.sock, line)
                                
                            # BAUTOCONNECT [1/0] ->  set autoconnect on or off
                            elif words_len > 0 and words[0].upper() == "BSHUTDOWN":
                                bouncer.send_pybnc_message(sock, "shutting down irc bouncer")
                                bouncer.send_pybnc_message(sock, "disconnecting from server %s (%s)" % (bouncer.cfg['server'], bouncer.real_server_name))
                                if words_len > 1:
                                    quit_message = words[1:]
                                    mirc.quit(bouncer.sock, quit_message)
                                else:
                                    mirc.quit(bouncer.sock)
                                    
                                for s in is_readable:
                                    s.close()
                                    
                                sys.exit()                                
                                    
                            # send anything else to ircd through irc client
                            else:
                                mirc.send(bouncer.sock, line)                            
                                    
            for sock in sel_write:
                pass
                
        except KeyboardInterrupt:
            logging.warning('got interrupt, closing sockets')
            
            for sock in is_readable:
                sock.close()
            break    
            


