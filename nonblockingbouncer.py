import sys, socket
from pprint import pprint
import string as str
from random import randint
import select

class Bouncer(object):
    sock = False
    registered = False
    
    def __init__(self, config):
        print("starting bouncer..")
        self.config = config
        
        #self.connect()
        
    def get_config(self):
        return self.config
    
    def send(self, data):
        try:
            payload = data.encode('utf-8')
            #print(">> %s" % payload)
            self.sock.send(data.encode('utf-8') + "\n")
        except:
            sys.exit("can't send()")
    
    def connect(self):
        print("connecting to %s:%d" % (self.config['server'], self.config['port']))
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.config['server'], self.config['port']))
            
            #self.sock.setblocking(False)
            
            self.send("USER %s %s %s :pybnc" % (self.config['id'], '+iw', self.config['nick']))
            self.send("NICK %s" % self.config['nick']) # here we actually assign the nick to the bot
        except:
            sys.exit("can't connect to server..")
            
        print("connection ok..")
        
        self.loop()
                
    def disconnect(self):
        if self.sock != False:
            self.sock.close()
            
    def select_loop(self):
        is_readable = [ self.sock ]
        is_writable = []
        is_error = []
        
        while True:
            r, w, e = select.select(is_readable, is_writable, is_error, 0)
            
            
    
            
    def loop(self):
        buff = ''
        while(True):
            received = self.sock.recv(2048)
            if received == '':
                sys.exit("socket connection closed..")
            
            lines = received.encode('utf-8').split("\n")
            lines = filter(None, lines)
            
            for line in lines:
                line = line.strip()
                self.parse(line)
                
    def parse(self, line):
        #pprint("<< %s" % line)
        words = line.split(' ')
        
        if words[0].startswith(':'):
            self.network = words[0][1:]
            
        if words[1].isdigit():
            irc_code = words[1]
            
            self.reply_to_code(irc_code)
            
        # reply to PING
        if words[0].startswith('PING'):
            pong = words[1][1:]
            self.send("PONG :%s" % pong)
            
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
            

