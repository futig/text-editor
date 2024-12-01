import json
import random
import socket
import uuid
from queue import Queue
from threading import Thread, Lock

from common.operations_converter import *

server_address = ("localhost", 5000)


def get_response(sock):
    data = []
    while True:
        r = sock.recv(1024)
        data.append(r.decode())
        if len(r) < 1024:
            break
    return json.loads(''.join(data))


class TextSource:
    def __init__(self, source):
        self.source = source

    @abstractmethod
    def get_text(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def set_text(self, text: str):
        raise NotImplementedError


class Client:
    def __init__(self):
        self.guid: str = str(uuid.uuid1())
        self.waiting = Queue()
        self.previous_operation = None
        self.revision = 1
        self.waiting_ack = None
        self.sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = ('localhost', random.Random().randint(20000, 60000))
        # self.sender.settimeout(1)
        self.receiver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.receiver.bind(self.addr)
        # self.receiver.settimeout(1)
        self.receiver.listen()
        self.connected = False
        self.file_id = None
        self._doc_state = ""
        self.server_sender = None
        self.lock = Lock()
        self.text_source: TextSource = None

    @property
    def doc_state(self):
        return self._doc_state

    @doc_state.setter
    def doc_state(self, text: str):
        self._doc_state = text
        # self.text_source.set_text(text)

    def set_text_source(self, text_source: TextSource):
        self.text_source = text_source

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
                response = get_response(self.server_sender)
                print(response)
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
        if type(operation) in {CreateServerOperation, ConnectServerOperation}:
            return
        self.doc_state = operation.do(self.doc_state)

    def create_request(self, operation):
        dict = {
            'file_id': self.file_id,
            'user_id': self.guid,
            'operation': operation.to_dict(),
            'revision': self.revision
        }
        return json.dumps(dict)

    def connect_to_server(self, file_id):
        operation = ConnectServerOperation(file_id)
        for i in range(3):
            try:
                self.sender.connect(server_address)
                request = {
                    'operation': operation.to_dict(),
                    'user_id': self.guid,
                    'addr': self.addr,
                    'file_id': file_id
                }
                dump = json.dumps(request)
                self.sender.sendall(dump.encode())
            except socket.error:
                continue
            finally:
                sock, addr = self.receiver.accept()
                response = get_response(sock)
                self.server_sender = sock
                print(response)
                if response['file_id']:
                    self.file_id = response['file_id']
                    self.doc_state = response['file']
                    self.connected = True
                    Thread(target=self.receive).start()
                    Thread(target=self.send).start()
                break

    def create_server(self, file: TextSource):
        cl = self

        def create_server_function():
            operation = CreateServerOperation(file.get_text())
            for i in range(3):
                try:
                    cl.sender.connect(server_address)
                    request = {
                        'operation': operation.to_dict(),
                        'user_id': cl.guid,
                        'addr': cl.addr
                    }
                    dump = json.dumps(request)
                    cl.sender.sendall(dump.encode())
                except socket.error:
                    continue
                finally:
                    sock, addr = cl.receiver.accept()
                    cl.server_sender = sock
                    response = get_response(sock)
                    print(response)
                    if response['file_id']:
                        self.file_id = response['file_id']
                        self.connected = True
                        Thread(target=cl.receive).start()
                        Thread(target=cl.send).start()
                    break

        return create_server_function
