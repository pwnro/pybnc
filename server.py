import sys, socket
import string as str
from random import randint

class Server(object):
    
    def __init__(self, config):
        print("starting server..")
        self.config = config
        
        self.connect()
        
