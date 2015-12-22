import sys
import socket
import logging

class MyIrc(object):
    @staticmethod
    def send(sock, data):
        bytes_sent = 0
        
        try:
            if type(data) is str:
                pass
            elif type(data) is bytes:
                data = data.decode('utf-8')
            
            data = data.strip()
            
            if len(data) > 0 and data[-1] != "\n":
                data = data + "\n"
                
            data = data.encode('utf-8')
            
            bytes_sent = sock.send(data)
                
        except Exception as e:
            logging.error("my_irc: can't send()")
            logging.error(repr(e))
            
        return bytes_sent
    
    @classmethod
    def privmsg(irc, sock, dest, line):
        return irc.send(sock, "PRIVMSG %s :%s" % (dest, line))
    
    @classmethod
    def notice(irc, sock, dest, line):
        return irc.send(sock, "NOTICE %s :%s" % (dest, line))
    
    @classmethod
    def ctcpSend(irc, sock, dest, command, value = ''):
        special_char = chr(1)
        
        if value:
            value = ' ' + value
        
        payload = "%s%s%s%s" % (special_char, command, value, special_char)
        
        return irc.privmsg(sock, dest, payload)
    
    @classmethod
    def ctcpReply(irc, sock, dest, command, value = ''):
        special_char = chr(1)
        
        if value:
            value = ' ' + value
        
        payload = "%s%s%s%s" % (special_char, command, value, special_char)
        
        return irc.notice(sock, dest, payload)    
                
    @classmethod
    def quit(irc, sock, message = False):
        if message:
            return irc.send(sock, "QUIT :%s" % message)    
        else:
            return irc.send(sock, "QUIT")
        
    @classmethod
    def setAway(irc, sock, message):
        return irc.send(sock, "AWAY :%s" % message)
    
    @classmethod
    def removeAway(irc, sock):
        return irc.send(sock, "AWAY")
    
    @classmethod
    def info(irc, sock):
        return irc.send(sock, "INFO")
    
    @classmethod
    def info(irc, sock):
        return irc.send(sock, "INFO")
    
    @classmethod
    def invite(irc, sock, nick, channel):
        return irc.send(sock, "INVITE %s %s" % (nick, channel))
        
    @classmethod
    def join(irc, sock, channel, key = False):
        if key:
            return irc.send(sock, "JOIN %s :%s" % (channel, key))    
        else:
            return irc.send(sock, "JOIN %s" % channel)
        
    @classmethod
    def kick(irc, sock, channel, nick, message = False):
        if message:
            return irc.send(sock, "KICK %s %s :%s" % (channel, nick, message))    
        else:
            return irc.send(sock, "KICK %s %s" % (channel, nick))    
        
    @classmethod
    def mode(irc, sock, modes):
        return irc.send(sock, "MODE %s" % modes)
    
    @classmethod
    def names(irc, sock, channel):
        return irc.send(sock, "NAMES %s" % channel)
    
    @classmethod
    def nick(irc, sock, nick):
        return irc.send(sock, "NICK %s" % nick)    

    @classmethod        
    def part(irc, sock, channel, message = False):
        if message:
            return irc.send(sock, "PART %s :%s" % (channel, message))
        else:
            return irc.send(sock, "PART %s" % channel)
        
    @classmethod
    def topic(irc, sock, channel, topic = False):
        if topic:
            return irc.send(sock, "TOPIC %s :%s" % (channel, topic))
        else:
            return irc.send(sock, "TOPIC %s" % channel)
  
    def parse(self, line):
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
    
    def reply_to_code(self, code):
        if code == "433" and self.registered == False:
            # generate new nick and send it to ircd
            newnick = "%s%d" % (self.getNick(), randint(1, 100))
            self.send("NICK %s" % newnick)
            
        if code == "001" and self.registered == False:
            # registed on the network
            self.registered = True

    # config is a dictionary with the following required keys: server, port, id, nick, description
    @classmethod
    def connect(irc, config):        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((config['server'], config['port']))
        
        #config['peername'] = sock.getpeername()
        
        if 'pass' in config:
            sock.send("PASS %s" % config['pass'])
        
        #sock.send("USER %s %s %s :%s" % (config['id'], '+iw', config['nick'], config['description']))
        #sock.send("NICK %s" % config['nick'])
        
        irc.send(sock, "USER %s %s %s :%s" % (config['user'], '+iw', config['nick'], config['description']))
        irc.send(sock, "NICK %s" % config['nick'])        

        return sock
    
    @classmethod
    def recv(irc, sock):
        lines = []
        buff_len = 2048
        
        try: 
            received = sock.recv(buff_len)                    
        except:
            return False
        
        try:
            lines = received.decode('utf-8').split("\n")
        except:
            lines = received
            
        lines = list(map(lambda l: l.strip(), lines))
        lines = list(filter(None, lines))
        
        return lines
    
    