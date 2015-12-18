import sys, os, json
import select
from hashlib import md5

from my_irc import MyIrc as mirc
import bnc


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


if hasattr(os, 'geteuid') and os.getuid() == 0:
    sys.exit("can't run as root srry")

try:
    with open('config.json') as cfg_file:
        cfg = json.load(cfg_file)
except:
    sys.exit("can't read config file config.json")

if 'bouncer' not in cfg or 'server' not in cfg:
    sys.exit("config file si fucked up bro")

# lists for select()
is_readable = []
is_writable = []
is_error = []

# fire up the bouncer
bouncer = bnc.Conn(cfg['bouncer'])
if bouncer.sock != False:
    add_socket(bouncer.sock)
else:
    sys.exit("could not create bouncer socket")
        
server = bnc.Server(cfg['server'])
if server.sock != False:
    add_socket(server.sock)
else:
    sys.exit("server can't start, shutting down")
    
# main select() loop
while True:
    try:
        sel_read, sel_write, sel_error = select.select(is_readable, is_writable, is_error)
        
        for sock in sel_error:
            # remove from lists
            print("select() error detected, removing sock")
            remove_socket(sock)
        
        for sock in sel_read:
            # incoming data from the ircd to the bouncer
            if sock == bouncer.sock:
                lines = mirc.recv(sock)
                
                if not lines:
                    print("bouncer disconnected from server")
                    remove_socket(sock)
                    continue
                
                #print(lines)
                
                # feed the bouncer cu ce zice ircdu
                for line in lines:
                    # va trimite automat si catre clientul conectat la server, daca e conectat
                    bouncer.parse(line)
                        
            # conexiune noua pe server
            elif sock == server.sock:
                client, address = server.sock.accept()
                print("server - new connection %d from %s" % (client.fileno(), address))
                
                # add client socket to select() loop
                add_socket(client)
            
            # de la unul din clientii conectati la server
            else:
                lines = mirc.recv(sock)
                
                if not lines:
                    print("client disconnected from server")
                    bouncer.client_sockets.remove(sock)
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
                            print("bnc client disconnected, intercepting QUIT")
                            remove_socket(sock)
                                
                        # send anything else to ircd through irc client
                        else:
                            mirc.send(bouncer.sock, line)
                                
        for sock in sel_write:
            pass
            
    except KeyboardInterrupt:
        print('got interrupt, closing sockets')
        
        for sock in is_readable:
            sock.close()
        break    
        
