import sys, socket
import signal

class BncServer(object):
    backlog = 5
    port = 0
    sock = False
    
    def __init__(self, config):
        print("starting server..")
        self.config = config
        self.port = config['port']
        
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