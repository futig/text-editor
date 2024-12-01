import asyncio
import socket
from queue import Queue
import json
import uuid
from threading import Thread, Lock
from collections import defaultdict

from common.operations_converter import convert_operation
from common.operations import *


class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.pending_processing = Queue()
        self.doc_state = defaultdict(str)
        self.connected_users = {}
        self.previous_operations = {}
        self.thread = Thread(target=self.process_requests).start()
        self.lock = Lock()
        self.previous_operation = None

    async def handle_client(self, reader, writer):
        while True:
            request = []
            while True:
                data = (await reader.read(1024)).decode('utf8')
                request.append(data)
                if len(data) < 1024:
                    break
            request = json.loads("".join(request))

            self.pending_processing.put((writer, request))

    def process_requests(self):
        while True:
            writer, request = self.pending_processing.get()
            operation = request['operation']
            operation = operation_from_json(operation)
            request['operation'] = operation

            previous_operation = None
            text = None
            if 'file_id' in request:
                if request['file_id'] in self.previous_operations:
                    previous_operation = self.previous_operations[request['file_id']]
            else:
                text = self.doc_state[request['file_id']] 
                
            applied_operation = self.apply_operation(request, previous_operation, text)
            
            self.send_to_users(request, applied_operation)

    def send_to_users(self, request, applied_operation):
        file_id = request['file_id']
        ack = {"operation": "ack", "file_id": file_id}
        
        if type(applied_operation) in {ConnectServerOperation, CreateServerOperation}:
            ack["file"] = self.doc_state[file_id]
            ack = json.dumps(ack).encode()
            self.connected_users[file_id][request['user_id']].sendall(ack)
            return
        
        ack = json.dumps(ack).encode()
        share = json.dumps({"operation": applied_operation.to_dict()}).encode()
        
        for user, conn in self.connected_users[file_id]:
            if request['user_id'] == user:
                conn.sendall(ack)
            else:
                conn.sendall(share)

    def apply_operation(self, request, previous_operation, text):
        operation = request['operation']
        if type(operation) is CreateServerOperation:
            id = str(uuid.uuid1())
            self.lock.acquire()
            self.doc_state[id] = operation.file
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(tuple(request['addr']))
            self.connected_users[id] = {request['user_id']: sock}
            self.lock.release()
            request['file_id'] = id
            return operation

        if type(operation) is ConnectServerOperation:
            server_to_connect = operation.file_id
            self.lock.acquire()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(tuple(request['addr']))
            self.connected_users[server_to_connect][request['user_id']] = sock
            self.lock.release()
            return operation

        if previous_operation:
            operation = convert_operation(operation, previous_operation)
            
        self.lock.acquire()
        self.previous_operations[request['file_id']] = operation
        self.doc_state[request['file_id']] = operation.do(text)
        self.lock.release()
        
        return operation


async def start_server():
    server = Server('localhost', 5000)
    async with await asyncio.start_server(server.handle_client, server.ip, server.port) as s:
        await s.serve_forever()


asyncio.run(start_server())
