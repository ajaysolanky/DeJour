import boto3
import logging

class ResultPublisher:
    def __init__(self, event, connection_id):
        domain = event.get('requestContext', {}).get('domainName')
        stage = event.get('requestContext', {}).get('stage')
        self.connection_id = connection_id
        self.apigatewaymanagementapi = boto3.client('apigatewaymanagementapi', endpoint_url=f'https://{domain}/{stage}')

    def post_to_connection(self, message):
        try:
            self.apigatewaymanagementapi.post_to_connection(ConnectionId=self.connection_id, Data=message)
        except Exception as e:
            logging.error('Failed to post message to connection {}: {}'.format(self.connection_id, str(e)))

class DebugPublisher:
    def post_to_connection(self, message):
        logging.info('DebugPublisher: {}'.format(message))
