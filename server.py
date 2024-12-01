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
        self.document_text = ""
        self.text_actuality = 0
        self.previous_actuality = 4095
        self.connected_users = {}
        self.thread = Thread(target=self.process_requests).start()
        self.lock = Lock()
        self.previous_operation = None


    def increment_text_actuality(self):
        self.previous_actuality = self.text_actuality
        self.text_actuality = (self.text_actuality + 1) % 4096


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
            request_new = json.loads("".join(request))
            self.pending_processing.put(request_new)

    def process_requests(self):
        while True:
            request = self.pending_processing.get()
            operation = request['operation']
            operation = operation_from_json(operation)
            request['operation'] = operation
            applied_operation, ok = self.apply_operation(request)
            print(f"{self.document_text}\n\n")
            self.send_to_users(request, applied_operation, ok)

    def send_to_users(self, request, applied_operation, success):
        response = {"actuality": self.text_actuality}
        if not success:
            response["file"] = self.document_text
            response["operation"] = "deny"
            response = json.dumps(response).encode()
            self.connected_users[request['user_id']].sendall(response)
            return
        
        if type(applied_operation) is ConnectServerOperation:
            response["file"] = self.document_text
            response["operation"] = "ack"
            response = json.dumps(response).encode()
            self.connected_users[request['user_id']].sendall(response)
            return
        
        response["operation"] = "ack"
        ack = json.dumps(response).encode()
        response["operation"] = applied_operation.to_dict()
        share = json.dumps(response).encode()

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
            return operation, True

        actuality = int(request['actuality'])
        if self.previous_actuality != actuality and self.text_actuality != actuality:
            return operation, False

        if self.previous_actuality == actuality and self.previous_operation:
            operation = convert_operation(operation, self.previous_operation)
            
        with self.lock:
            self.previous_operation = operation
            self.document_text = operation.do(self.document_text)
            self.increment_text_actuality()
        
        return operation, True


async def start_server():
    server = Server('localhost', 5000)
    async with await asyncio.start_server(server.handle_client, server.ip, server.port) as s:
        await s.serve_forever()


asyncio.run(start_server())
