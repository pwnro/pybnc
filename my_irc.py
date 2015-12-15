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
            #payload = bytes(data + "\n", 'UTF-8')
            
            for client_socket in self.client_sockets:
                try:
                    #client_socket.send(payload)
                    self.send_to_socket(data, client_socket)
                except:
                    print("could not send data read from ircd to client")
                    # remove client_socket from list
                    self.client_sockets.remove(client_socket)
    
    def send_to_socket(self, data, socket):
        self.send(data, socket)
    
    def send(self, data, to_client = False):
        try:
            if type(data) is str:
                pass
            elif type(data) is bytes:
                data = data.decode('utf-8')
            
            if len(data) > 0 and data[-1] != "\n":
                print("**********")
                print(data)
                print("**********")                
                
                data = data + "\n"
                
            data = data.encode('utf-8')
            
            if to_client == False:
                self.sock.send(data)
            else:
                to_client.send(data)
                
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
                
    def join_config_channels(self):        
        # join channels
        for channel in self.config['channels']:
            self.send("JOIN %s" % channel)
        
            

