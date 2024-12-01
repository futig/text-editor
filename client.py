import json
import random
import socket
import uuid
from queue import Queue
from threading import Thread, Lock

from common.operations_converter import *

server_address = ("localhost", 5000)

class Client:
    def __init__(self):
        self.guid: str = str(uuid.uuid1())
        self.waiting = Queue()
        self.waiting_ack = None
        self.state_updated = False
        
        self.addr = ('localhost', random.Random().randint(20000, 60000))
        self.receiver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.receiver.bind(self.addr)
        self.receiver.listen()
        
        self.sender = None
        self.server_con = None
        self.connect_to_server()

        self.connected = False
        self.doc_state = ""
        self.lock = Lock()

    def put_operation_in_waiting(self, operation):
        self.waiting.put(operation)

    def send(self):
        while True:
            if self.waiting_ack or self.waiting.empty():
                continue
            self.lock.acquire()
            operation = self.waiting.get()
            request = self.create_request(operation)
            self.sender.send(request.encode())
            self.waiting_ack = operation
            self.lock.release()

    def receive(self):
        while self.connected:
            try:
                response = self.get_response(self.server_con)
                if response['operation'] == 'ack':
                    self.lock.acquire()
                    self.waiting_ack = None
                    self.lock.release()
                else:
                    operation = operation_from_json(response['operation'])
                    self.apply_changes(operation)
            except socket.error:
                raise socket.error

    def apply_changes(self, operation):
        if type(operation) is ConnectServerOperation:
            return
        self.doc_state = operation.do(self.doc_state)
        self.state_updated = True

    def create_request(self, operation):
        dict = {
            'user_id': self.guid,
            'operation': operation.to_dict(),
            'revision': self.revision
        }
        return json.dumps(dict)

    def connect_to_server(self):
        self.sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        operation = ConnectServerOperation()
        try:
            self.sender.connect(server_address)
            request = {
                'operation': operation.to_dict(),
                'user_id': self.guid,
                'addr': self.addr,
            }
            dump = json.dumps(request)
            self.sender.sendall(dump.encode())
        except socket.error:
            return
        finally:
            sock, _ = self.receiver.accept()
            response = self.get_response(sock)
            self.server_con = sock
            if response['file']:
                self.doc_state = response['file']
                self.connected = True
                Thread(target=self.receive).start()
                Thread(target=self.send).start()
            
    
    def get_response(self, sock):
        data = []
        while True:
            r = sock.recv(1024)
            data.append(r.decode())
            if len(r) < 1024:
                break
        return json.loads(''.join(data))
