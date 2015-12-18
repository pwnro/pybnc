import sys, socket
import signal
from random import randint
from my_irc import MyIrc as mirc

# irc connection bouncer
class Conn(object):
    port = 0
    sock = False
    
    registered = False

    cfg = {}    
    client_sockets = []
    
    real_server_name = ''
    nick = ''
    userhost = ''
    
    def send(self, line):
        return mirc.send(self.sock, line)
    
    
    def __init__(self, cfg):
        self.cfg = cfg
        
        self.real_server_name = cfg['server']
        self.nick = cfg['nick']
        
        print("starting bouncer %s" % self.cfg['id'])
        self.sock = mirc.connect(self.cfg)
        
        if self.userhost == '':
            self.userhost = cfg['nick'] + '!~' + cfg['id'] + self.sock.getsockname()[0]

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
                    print("could not send data read from ircd to client")
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
                pass
            
            self.after_register()
        
    def sighandler(self, signum, frame):
        # close the server
        print('received kb interrupt, shutting down bnc client socket')
        self.sock.close()
        
    def setup_user(self, client):
        mirc.send(client, ":pyBNC 001 %s :welcome to pyBNC" % self.nick)
        mirc.send(client, ":pyBNC 002 %s :running pyBNC version 1.3.37" % self.nick)
        
        for channel in self.cfg['channels']:
            mirc.join(self.sock, channel)
            
            # emulate joining the channel in case we're already on the channel
            mirc.send(client, ':%s JOIN %s' % (self.userhost, channel))
            
            mirc.names(self.sock, channel)
            
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
        
        print("starting server..")
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', self.port))
        
        print('listening on port %d' % self.port)
        
        self.sock.listen(self.backlog)        
        
        # Trap keyboard interrupts
        signal.signal(signal.SIGINT, self.sighandler)
        
    def sighandler(self, signum, frame):
        # close the server
        print('received kb interrupt, shutting down server')
        self.sock.close()
