import sys, socket
#import irc
from pprint import pprint
import string as str

class Bouncer(object):
    conn = False
    
    def __init__(self, config):
        print("starting bouncer..")
        self.config = config
        
        self.connect()
        
    def get_config(self):
        return self.config
    
    def send(self, data):
        try:
            self.conn.send(bytes(data, 'UTF-8'))
        except:
            sys.exit("can't send()")
    
    def connect(self):
        print("connectng to %s:%d" % (self.config['server'], self.config['port']))
        
        try:
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn.connect((self.config['server'], self.config['port']))
            
            self.send("USER %s %s %s :pybnc\n" % (self.config['id'], '+iw', self.config['nick']))
            self.send("NICK %s\n") # here we actually assign the nick to the bot
        except:
            sys.exit("can't connect to server..")
            
        print("connection ok..")
        
        self.loop()
                
    def disconnect(self):
        if self.conn != False:
            self.conn.close()
            
    def loop(self):
        buff = ''
        while(True):
            buff = buff + self.conn.recv(1024).decode("UTF-8")
            
            pprint(buff)
            temp = buff.split("\n")
            buff = temp.pop()
            
            for line in buff:
                line = line.strip()
                self.parse(line)
                
    def parse(self, line):
        words = line.split()
        
        print(line)
    
        

