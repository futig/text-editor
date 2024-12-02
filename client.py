import difflib
import json
import random
import socket
import uuid
from queue import Queue
from threading import Thread, Lock

from common import operations
from common.operations_converter import *

server_address = ("localhost", 5000)

class Client:
    def __init__(self):
        self.guid: str = str(uuid.uuid1())
        self.waiting = Queue()
        self.waiting_operation = None
        self.state_updated = False
        self.document_text = ""
        self.uncheked_text = ""
        self.text_actuality = 0

        
        self.addr = ('localhost', random.Random().randint(20000, 60000))
        self.receiver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.receiver.bind(self.addr)
        self.receiver.listen()
        
        self.sender = None
        self.server_con = None
        self.connect_to_server()

        self.lock = Lock()

    def is_updated(self):
        return self.state_updated
    
    def done_update(self):
        with self.lock:
            self.state_updated = False

    def put_operation_in_waiting(self, operation):
        with self.lock:
            self.waiting.put(operation)

    def send_operations(self, current_text):
        while True:
            matcher = difflib.SequenceMatcher(None, self.uncheked_text, current_text)
            opcodes = matcher.get_opcodes()
            if len(opcodes) == 0:
                break
            if opcodes[0][0] in {'equal', "replace"}:
                if len(opcodes) == 1:
                    break
                opcode = opcodes[1]
            else:
                opcode = opcodes[0]
            operation = None
            if opcode[0] == 'insert':
                inserted_text = current_text[opcode[3]:opcode[4]]
                index = opcode[1]
                operation = operations.InsertOperation(index, inserted_text)
            elif opcode[0] == 'delete':
                begin = opcode[1]
                end = opcode[2]
                operation = operations.DeleteOperation(begin, end)
            if operation:
                self.put_operation_in_waiting(operation)
                self.uncheked_text = operation.do(self.uncheked_text)
                continue
            break
                
    def send(self):
        while True:
            if self.waiting_operation or self.waiting.empty():
                continue
            with self.lock:
                self.waiting_operation = self.waiting.get()
                request = self.create_request(self.waiting_operation)
                self.sender.send(request.encode())

    def receive(self):
        while True:
            try:
                response = self.get_response(self.server_con)
                if response['operation'] == 'ack':
                    with self.lock:
                        self.waiting.task_done()
                        self.document_text = self.waiting_operation.do(self.document_text)
                        self.waiting_operation = None
                        self.text_actuality = response['actuality']
                        continue    
                elif response['operation'] == 'deny':
                    with self.lock:
                        self.waiting = Queue()
                        self.document_text = self.uncheked_text = response['file']
                        self.text_actuality = response['actuality']
                        self.state_updated = True
                else:
                    operation = operation_from_json(response['operation'])
                    with self.lock:
                        self.text_actuality = response['actuality']
                        if type(operation) is ConnectServerOperation:
                            continue
                        self.waiting = Queue()
                        self.document_text = operation.do(self.document_text)
                        self.uncheked_text = self.document_text
                        self.state_updated = True
                
            except socket.error:
                raise socket.error

    def create_request(self, operation):
        dict = {
            'user_id': self.guid,
            'actuality': self.text_actuality,
            'operation': operation.to_dict(),
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
            self.document_text = response['file']
            self.uncheked_text = self.document_text
            self.text_actuality = response['actuality']
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
