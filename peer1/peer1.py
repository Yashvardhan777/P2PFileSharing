import socket
import threading
import platform
import mimetypes
import os
import sys
import time
from pathlib import Path

#=================================================== Peer Class ===============================================================
class Peer(object):
    #========================================= Initialise all the variables =========================================
    def __init__(self, serverHost='localhost', version='P2P/1.0', directory='files'):
        self.serverHost = serverHost
        self.serverPort = 3000
        self.version = version
        self.directory = directory 
        Path(self.directory).mkdir(exist_ok=True)
        self.uploadPort = None
        self.ifShareable = True
    #================================================================================================================


    #================================================ Setting up peer ===============================================
    #================================================== Start peer ==================================================
    def startPeer(self):
        # CONNECTING TO THE SERVER USING SOCKET MODULE
        print('Connecting to the server',self.serverHost,":"+str(self.serverPort))
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.server.connect((self.serverHost, self.serverPort))
        except Exception:
            print('Server Currently Unavailable')
            return

        print('Connected')
        # INITIALISING THE UPLOADING PROCESS
        uploaderProcess = threading.Thread(target=self.initUpload)
        uploaderProcess.start()
        while self.uploadPort is None:
            # WAIT UNTIL THE UPLOAD PORT HAS BEEN INITIALISED
            pass
        print('Listening to the upload port:',self.uploadPort)

        # START INTERACTIVE SHELL
        self.commandLineInterface()
    #================================================================================================================

    #=============================================== Interactive shell ==============================================
    def commandLineInterface(self):
        #LIST OF PROCESSES ONE CAN PERFORM
        commands = {'1': self.addPeer,
                    '2': self.findPeer,
                    '3': self.listAllPeers,
                    '4': self.preDownloadProcessing,
                    '5': self.shutdownPeer}
        while True:
            try:
                choice = input('\n1: Add file to current peer \n2: Find given file \n3: List all files available \n4: Download file \n5: Shut Down \nEnter your choice: ')
                commands.setdefault(choice, self.invalidInput)()
            except MyException as e:
                print(e)
            except Exception:
                print('System Error')
            except BaseException:
                self.shutdownPeer()
    #================================================================================================================
    #================================================================================================================


    #================================================ Process Handlers ================================================
    #=========================================== Add files to current peer ============================================
    def addPeer(self, n=None, title=None):
        # THIS PROCESS ADDS THE FILES TO THE CURRENT PEER FOR OTHER PEERS TO SEE AND ACCESS THOSE FILES
        if not n:
            n = input('Enter the file number: ')
            if not n.isdigit():
                raise MyException('Invalid Input')
            title = input('Enter the file title: ')
        file = Path('%s/test%s.txt' % (self.directory, n))
        print(file)
        if not file.is_file():
            raise MyException('File does not exist')
        message = 'ADD TEST %s %s\n' % (n, self.version)
        message += 'Host: %s\n' % socket.gethostname()
        message += 'Post: %s\n' % self.uploadPort
        message += 'Title: %s\n' % title
        self.server.sendall(message.encode())
        result = self.server.recv(1024).decode()
        print('Recieve response: \n%s' % result)
    #================================================================================================================
    
    #===================================== Search for the files in all of the peers =====================================
    def findPeer(self):
        num = input('Enter the file number: ')
        title = input('Enter the file title(optional): ')
        message = 'FIND Peer FILE %s %s\n' % (num, self.version)
        message += 'Host: %s\n' % socket.gethostname()
        message += 'Post: %s\n' % self.uploadPort
        message += 'Title: %s\n' % title
        self.server.sendall(message.encode())
        result = self.server.recv(1024).decode()
        print('Recieve response: \n%s' % result)
    #================================================================================================================

    #========================================= List all  files available =========================================
    def listAllPeers(self):
        m1 = 'LIST ALL %s\n' % self.version
        m2 = 'Host: %s\n' % socket.gethostname()
        m3 = 'Post: %s\n' % self.uploadPort
        message = m1 + m2 + m3
        self.server.sendall(message.encode())
        result = self.server.recv(1024).decode()
        print('Recieve response: \n%s' % result)
    #=================================================================================================================

    #======================================== Initialise the uploading process =======================================
    def initUpload(self):
        # listen upload port
        self.uploader = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.uploader.bind(('', 0))
        self.uploadPort = self.uploader.getsockname()[1]
        self.uploader.listen(5)

        while self.ifShareable:
            requester, add = self.uploader.accept()
            handler = threading.Thread(
                target=self.handleUpload, args=(requester, add))
            handler.start()
        self.uploader.close()
    #================================================================================================================

    #========================================== Handle uploading process ============================================
    def handleUpload(self, soc, add):
        header = soc.recv(1024).decode().splitlines()
        try:
            version = header[0].split()[-1]
            num = header[0].split()[-2]
            method = header[0].split()[0]
            path = '%s/test%s.txt' % (self.directory, num)
            if version != self.version:
                soc.sendall(str.encode(self.version + ' 505 P2P Version Not Supported\n'))
            elif not Path(path).is_file():
                soc.sendall(str.encode(self.version + ' 404 Not Found\n'))
            elif method == 'GET':
                header = self.version + ' 200 OK\n'
                header += 'Data: %s\n' % (time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()))
                header += 'OS: %s\n' % (platform.platform())
                header += 'Last-Modified: %s\n' % (time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(os.path.getmtime(path))))
                header += 'Content-Length: %s\n' % (os.path.getsize(path))
                header += 'Content-Type: %s\n' % (mimetypes.MimeTypes().guess_type(path)[0])
                soc.sendall(header.encode())
                # Uploading
                try:
                    print('\nUploading...')
                    sendLength = 0
                    with open(path, 'r') as file:
                        toSend = file.read(1024)
                        while toSend:
                            sendLength += len(toSend.encode())
                            soc.sendall(toSend.encode())
                            toSend = file.read(1024)
                except Exception:
                    raise MyException('Uploading Failed')
                print('Uploading Completed.')
                # Restore the command line interface
                print(
                    '\n1: Add file to current peer \n2: Find test file \n3: List all files available \n4: Download file\nEnter your request: ')
            else:
                raise MyException('Bad Request.')
        except Exception:
            soc.sendall(str.encode(self.version + '  400 Bad Request\n'))
        finally:
            soc.close()
    #================================================================================================================

    #=========================================== pre-download processing ============================================
    def preDownloadProcessing(self):
        num = input('Enter the test file number: ')
        message = 'FIND TEST  %s %s\n' % (num, self.version)
        message += 'Host: %s\n' % socket.gethostname()
        message += 'Post: %s\n' % self.uploadPort
        message += 'Title: Unkown\n'
        self.server.sendall(message.encode())
        lines = self.server.recv(1024).decode().splitlines()
        if lines[0].split()[1] == '200':
            # Choose a peer
            print('Available peers: ')
            for i, line in enumerate(lines[1:]):
                line = line.split()
                print('%s: %s:%s' % (i + 1, line[-2], line[-1]))

            try:
                id = int(input('Choose one peer to download: '))
                title = lines[id].rsplit(None, 2)[0].split(None, 2)[-1]
                peerHost = lines[id].split()[-2]
                peerPort = int(lines[id].split()[-1])
            except Exception:
                raise MyException('Invalid Input.')
            # exclude self
            if((peerHost, peerPort) == (socket.gethostname(), self.uploadPort)):
                raise MyException('Do not choose yourself.')
            # send get request
            self.download(num, title, peerHost, peerPort)
        elif lines[0].split()[1] == '400':
            raise MyException('Invalid Input.')
        elif lines[0].split()[1] == '404':
            raise MyException('File Not Available.')
        elif lines[0].split()[1] == '500':
            raise MyException('Version Not Supported.')
    #================================================================================================================

    #============================================== Download  file ==================================================
    def download(self, num, title, peerHost, peerPort):
        try:
            # make connnection
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # connect_ex return errors
            if soc.connect_ex((peerHost, peerPort)):
                # print('Try Local Network...')
                # if soc.connect_ex(('localhost', peerPort)):
                raise MyException('Peer Not Available')
            # make request
            message = 'GET  %s %s\n' % (num, self.version)
            message += 'Host: %s\n' % socket.gethostname()
            message += 'OS: %s\n' % platform.platform()
            soc.sendall(message.encode())

            # Downloading

            header = soc.recv(1024).decode()
            print('Recieve response header: \n%s' % header)
            header = header.splitlines()
            if header[0].split()[-2] == '200':
                path = '%s/test%s.txt' % (self.directory, num)
                print('Downloading...')
                try:
                    with open(path, 'w') as file:
                        content = soc.recv(1024)
                        while content:
                            file.write(content.decode())
                            content = soc.recv(1024)
                except Exception:
                    raise MyException('Downloading Failed')

                total_length = int(header[4].split()[1])
                # print('write: %s | total: %s' % (os.path.getsize(path), total_length))

                if os.path.getsize(path) < total_length:
                    raise MyException('Downloading Failed')

                print('Downloading Completed.')
                # Share file, send ADD request
                print('Sending ADD request to share...')
                if self.ifShareable:
                    self.addPeer(num, title)
            elif header[0].split()[1] == '400':
                raise MyException('Invalid Input.')
            elif header[0].split()[1] == '404':
                raise MyException('File Not Available.')
            elif header[0].split()[1] == '500':
                raise MyException('Version Not Supported.')
        finally:
            soc.close()
    #===============================================================================================================

    #============================================== ShutdownPeer peer ==============================================
    def shutdownPeer(self):
        print('\nShutting Down...')
        self.server.close()
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    #================================================================================================================
    #================================================================================================================


    #============================================== Exception Handling ==============================================
    def invalidInput(self):
        raise MyException('Invalid Input.')
    #================================================================================================================
#============================================================================================================================

#====================================================== Exception Class =======================================================
class MyException(Exception):
    pass
#==============================================================================================================================
#=================================================== Main Function ==========================================================
if __name__ == '__main__':
    if len(sys.argv) == 2:
        Peer = Peer(sys.argv[1])
    else:
        Peer = Peer()
    Peer.startPeer()
#============================================================================================================================