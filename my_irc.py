import sys, socket
from pprint import pprint
import string as str
from random import randint
import select

class IrcClient(object):
    sock = False
    registered = False
    client_connected = False
    client_sockets = []
    
    def __init__(self, config):
        print("starting bouncer..")
        self.config = config
        self.id = config['id']
        #self.connect()
        
    def get_config(self):
        return self.config
    
    def send_to_client_sockets(self, data):
        # data a fost decodata din bytes, primeste str, pentru trimitere encodam inapoi in bytes
        if self.client_sockets != []:
            data = data + "\n"
            
            print("************")
            print(type(data))
            print('%s' % data)
            print("************")
            
            #payload = bytes(data, 'UTF-8') -> trimite sub forma bytes pyton b'...
            payload = bytes(data, 'UTF-8')
            
            for client_socket in self.client_sockets:
                try:
                    client_socket.send(payload)
                except:
                    print("could not send data read from ircd to client")
                    # remove client_socket from list
                    self.client_sockets.remove(client_socket)
    
    def send(self, data):
        try:
            data = data + "\n"
            data = bytes(data, 'UTF-8')
            #payload = (str(data) + "\n").encode('utf-8')
            ##print(">> %s" % payload)
            
            payload = data
            
            self.sock.send(payload)
        except Exception as e:
            print(repr(e))
            sys.exit("can't send()")
    
    def connect(self):
        print("connecting to %s:%d" % (self.config['server'], self.config['port']))
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.config['server'], self.config['port']))
            
            #self.sock.setblocking(False)
            
            self.config['peername'] = self.sock.getpeername()
            
            self.send("USER %s %s %s :pybnc" % (self.config['id'], '+iw', self.config['nick']))
            self.send("NICK %s" % self.config['nick']) # here we actually assign the nick to the bot
        except Exception as e:
            print(repr(e))
            sys.exit("can't connect to server..")
            
        print("connection ok..")
        
        #return self.sock
        #self.select_loop()
                
    def disconnect(self):
        if self.sock != False:
            self.sock.close()
            
    def select_loop(self):
        is_readable = [ self.sock ]
        is_writable = [ self.sock ]
        is_error = []
        
        while True:
            try:
                r, w, e = select.select(is_readable, is_writable, is_error, 0)
                
                for sock in r:
                    if sock == self.sock:
                        # incoming message from ircd
                        received = sock.recv(4096)
                        
                        if not received:
                            sys.exit("disconnected from server")
                        else:
                            lines = received.encode('utf-8').split("\n")
                            
                            for line in lines:
                                self.parse(line.strip())
                                
            except KeyboardInterrupt:
                print('!!!! interrupted.')
                self.sock.close()
                break            
            
    def loop(self):
        buff = ''
        while(True):
            received = self.sock.recv(2048)
            if received == '':
                sys.exit("socket connection closed..")
            
            lines = str(received).encode('utf-8').split("\n")
            lines = filter(None, lines)
            
            for line in lines:
                line = line.strip()
                self.parse(line)
                
    def parse(self, line):
        #pprint("<< %s" % line)
        words = line.split(' ')
        words_len = len(words)
        
        if words_len > 0 and words[0].startswith(':'):
            self.network = words[0][1:]
            
        if words_len > 1 and words[1].isdigit():
            irc_code = words[1]
            
            self.reply_to_code(irc_code)
            
        # reply to PING
        if words[0].startswith('PING'):
            pong = words[1][1:]
            self.send("PONG :%s" % pong)
            
        if self.client_connected != False:
            self.send_to_client_sockets(line)
            
    def getNick(self):
        return self.config['nick']
    
    def reply_to_code(self, code):
        if code == "433" and self.registered == False:
            # generate new nick and send it to ircd
            newnick = "%s%d" % (self.getNick(), randint(1, 100))
            self.send("NICK %s" % newnick)
            
        if code == "001" and self.registered == False:
            # registed on the network
            self.registered = True
            
            # join channels
            for channel in self.config['channels']:
                self.send("JOIN %s" % channel)
            

