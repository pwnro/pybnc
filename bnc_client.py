import sys, socket
import signal

class BncClient(object):
    port = 0
    sock = False
    
    def __init__(self, sock):
        print("starting bnc client..")
        
        self.sock = sock
        
        signal.signal(signal.SIGINT, self.sighandler)
        
    def sighandler(self, signum, frame):
        # close the server
        print('received kb interrupt, shutting down bnc client socket')
        self.sock.close()