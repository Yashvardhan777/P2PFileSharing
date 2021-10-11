import socket
import threading
import os
import sys
from collections import defaultdict

#====================================================== Exception Class =======================================================
class MyException(Exception):
    pass
#==============================================================================================================================

#=================================================== Server Class =============================================================
class Server(object):
    #========================================= Initialise all the variables =========================================
    def __init__(self, host='', port=3000, version='P2P/1.0'):
        self.HOST = host
        self.PORT = port
        self.version = version
        self.peers = defaultdict(set)
        self.files = {}
        self.lock = threading.Lock()
    #================================================================================================================

    #================================================== Start server ================================================
    def startServer(self):
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.bind((self.HOST, self.PORT))
            self.s.listen(5)
            print('Server %s is listening on port %s' %(self.version, self.PORT))

            while True:
                soc, add = self.s.accept()
                print('%s:%s connected' % (add[0], add[1]))
                thread = threading.Thread(target=self.serverHandler, args=(soc, add))
                thread.start()

            # raise KeyboardInterrupt
        except KeyboardInterrupt:
            self.shutdownServer()
                
    #================================================================================================================

    #================================================== Server handler ==============================================
    # connect with a client
    def serverHandler(self, soc, add):
        # keep recieve request from client
        host = None
        port = None
        while True:
            try:
                request = soc.recv(1024).decode()
                print('Recieve request:\n%s' % request)
                lines = request.splitlines()
                version = lines[0].split()[-1]
                if version != self.version:
                    soc.sendall(str.encode(self.version + ' 505 P2P Version Not Supported\n'))
                else:
                    func = lines[0].split()[0]
                    if func == 'ADD':
                        host = lines[1].split(None, 1)[1]
                        port = int(lines[2].split(None, 1)[1])
                        num = int(lines[0].split()[-2])
                        title = lines[3].split(None, 1)[1]
                        self.addFile(soc, (host, port), num, title)
                    elif func == 'FIND':
                        num = int(lines[0].split()[-2])
                        self.getPeersOfFile(soc, num)
                    elif func == 'LIST':
                        self.getAllFiles(soc)
                    else:
                        raise AttributeError('Function does not match')
            except KeyboardInterrupt:
                self.serverHandler()
            except ConnectionError:
                print('%s:%s left' % (add[0], add[1]))
                # Clean data if necessary
                if host and port:
                    self.removePeer(host,port)
                soc.close()
                break
            except BaseException:
                try:
                    soc.sendall(str.encode(self.version + '  400 Bad Request\n'))
                except KeyboardInterrupt:
                    self.serverHandler()
                except ConnectionError:
                    print('%s:%s left' % (add[0], add[1]))
                    # Clean data if necessary
                    if host and port:
                        self.removePeer(host,port)
                    soc.close()
                    break
    #================================================================================================================

    #================================================== cleanup method ==============================================
    def removePeer(self, host, port):
        self.lock.acquire()
        nums = self.peers[(host, port)]
        for num in nums:
            self.files[num][1].discard((host, port))
        if not self.files[num][1]:
            self.files.pop(num, None)
        self.peers.pop((host, port), None)
        self.lock.release()
    #================================================================================================================

    #================================================ Add a new file ================================================
    def addFile(self, soc, peer, num, title):
        self.lock.acquire()
        try:
            self.peers[peer].add(num)
            self.files.setdefault(num, (title, set()))[1].add(peer)
        finally:
            self.lock.release()
        header = self.version + ' 200 OK\n'
        header += 'TEST %s %s %s %s\n' % (num,self.files[num][0], peer[0], peer[1])
        soc.sendall(str.encode(header))
    #================================================================================================================

    #============================================= Retrieve Peers for file ==========================================
    def getPeersOfFile(self, soc, num):
        self.lock.acquire()
        try:
            if num not in self.files:
                header = self.version + ' 404 Not Found\n'
            else:
                header = self.version + ' 200 OK\n'
                title = self.files[num][0]
                for peer in self.files[num][1]:
                    header += 'TEST %s %s %s %s\n' % (num, title, peer[0], peer[1])
        finally:
            self.lock.release()
        soc.sendall(str.encode(header))
    #================================================================================================================

    #============================================= Retrieve all the Files ===========================================
    def getAllFiles(self, soc):
        self.lock.acquire()
        try:
            if not self.files:
                header = self.version + ' 404 Not Found\n'
            else:
                header = self.version + ' 200 OK\n'
                for num in self.files:
                    title = self.files[num][0]
                    for peer in self.files[num][1]:
                        header += 'TEST %s %s %s %s\n' % (num, title, peer[0], peer[1])
        finally:
            self.lock.release()
        soc.sendall(str.encode(header))
    #================================================================================================================

    #================================================ Shutdown Server ===============================================
    def shutdownServer(self):
        print('\nShutting down the server..\nGood Bye!')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    #================================================================================================================
#==============================================================================================================================


#========================================================== Main Function =====================================================
if __name__ == '__main__':
    server = Server()
    server.startServer()
#==============================================================================================================================
