import json
import boto3
import logging
from abc import ABC, abstractmethod

class BasePublisher(ABC):
    BUFFER_LEN = 9

    def __init__(self) -> None:
        self.buffer = []
        self.finished = False

    @abstractmethod
    def send(self, message) -> None:
        pass

    def post_to_connection(self, message):
        if self.finished:
            return
        elif json.loads(message)['type'] == 'end':
            for msg in self.buffer:
                self.send(msg)
        else:
            self.buffer.append(message)
            buffer_str = "".join(json.loads(msg)['message'] for msg in self.buffer)
            if "SOURCES:" in buffer_str:
                end_str = ""
                while "SOURCES:" not in end_str:
                    last_msg = json.loads(self.buffer.pop())['message']
                    end_str = last_msg + end_str
                for msg in self.buffer:
                    self.send(msg)
                self.finished = True
                return
            if len(self.buffer) > self.BUFFER_LEN:
                to_send = self.buffer[:-1 * self.BUFFER_LEN]
                self.buffer = self.buffer[-1 * self.BUFFER_LEN:]
                for msg in to_send:
                    self.send(msg)

class ResultPublisher(BasePublisher):
    def __init__(self, event, connection_id):
        super().__init__()
        domain = event.get('requestContext', {}).get('domainName')
        stage = event.get('requestContext', {}).get('stage')
        self.connection_id = connection_id
        self.apigatewaymanagementapi = boto3.client('apigatewaymanagementapi', endpoint_url=f'https://{domain}/{stage}')

    def send(self, message):
        try:
            self.apigatewaymanagementapi.post_to_connection(ConnectionId=self.connection_id, Data=message)
        except Exception as e:
            logging.error('Failed to post message to connection {}: {}'.format(self.connection_id, str(e)))

    # def post_to_connection(self, message):
    #     try:
    #         self.apigatewaymanagementapi.post_to_connection(ConnectionId=self.connection_id, Data=message)
    #     except Exception as e:
    #         logging.error('Failed to post message to connection {}: {}'.format(self.connection_id, str(e)))

class DebugPublisher(BasePublisher):
    # def post_to_connection(self, message):
    #     msg_json = json.loads(message)
    #     print(msg_json.get('message'), end='', flush=True)

    def send(self, message):
        msg_json = json.loads(message)
        print(msg_json.get('message'), end='', flush=True)