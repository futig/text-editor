import asyncio
import socket
from queue import Queue
import json
from threading import Thread, Lock

from common.operations_converter import convert_operation
from common.operations import *


class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.pending_processing = Queue()
        self.doc_state = "kcsdnjcsd"
        self.connected_users = {}
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
            if request == [""]:
                return
            try:
                request_new = json.loads("".join(request))
            except:
                print()
                print(request)
                print()
            self.pending_processing.put((writer, request_new))

    def process_requests(self):
        while True:
            writer, request = self.pending_processing.get()
            operation = request['operation']
            operation = operation_from_json(operation)
            request['operation'] = operation
            applied_operation = self.apply_operation(request)
            self.send_to_users(request, applied_operation)

    def send_to_users(self, request, applied_operation):
        ack = {"operation": "ack"}
        
        if type(applied_operation) is ConnectServerOperation:
            ack["file"] = self.doc_state
            ack = json.dumps(ack).encode()
            self.connected_users[request['user_id']].sendall(ack)
            return
        
        ack = json.dumps(ack).encode()
        share = json.dumps({"operation": applied_operation.to_dict()}).encode()
        
        for user, conn in self.connected_users.items():
            if request['user_id'] == user:
                conn.sendall(ack)
            else:
                conn.sendall(share)

    def apply_operation(self, request):
        operation = request['operation']
        if type(operation) is ConnectServerOperation:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(tuple(request['addr']))
            self.lock.acquire()
            self.connected_users[request['user_id']] = sock
            self.lock.release()
            return operation

        if self.previous_operation:
            operation = convert_operation(operation, self.previous_operation)
            
        self.lock.acquire()
        self.previous_operation = operation
        self.doc_state = operation.do(self.doc_state)
        self.lock.release()
        
        return operation


async def start_server():
    server = Server('localhost', 5000)
    async with await asyncio.start_server(server.handle_client, server.ip, server.port) as s:
        await s.serve_forever()


asyncio.run(start_server())
