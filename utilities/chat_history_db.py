import boto3
import logging

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
logging.getLogger().setLevel(logging.INFO)

class ChatHistoryDB: 
    TABLE_NAME = "dejour_chat_history"
    def __init__(self):
        self.table = dynamodb.Table(self.TABLE_NAME)

    def put_item(self, Item):
        result = self.table.put_item(Item=Item)

    def query(self, key_condition_expression):
        return self.table.query(
            KeyConditionExpression=key_condition_expression,
            ConsistentRead=True)
            
    def delete_item(self, Key):
        self.table.delete_item(Key=Key)

class InMemoryDB: 
    def __init__(self):
        self.db = {}

    def put_item(self, Item):
        connection_id = Item["connectionid"]
        self.db[connection_id] = Item

    def query(self, KeyConditionExpression, ExpressionAttributeValues):
        connection_id = KeyConditionExpression["connectionid"]
        item = self.db.get(connection_id)
        return {
            "Item": [item]
        }

    def delete_item(self, Key):
        connection_id = Key["connectionid"]
        self.db.pop(connection_id, None)

class ChatHistoryService:
    def __init__(self, connectionid, db):
        self.connectionid = connectionid
        self.db = db

    def create_chat_history(self):
        data = {
            "connectionid": self.connectionid,
            "chat_history": []
        }
        self.db.put_item(Item=data)

    def update_chat_history(self, question, answer):
        response = self.db.query(key_condition_expression=boto3.dynamodb.conditions.Key('connectionid').eq(self.connectionid))
        items = response.get('Items', None)
        if items is None or len(items) == 0:
            raise Exception("No chat history found")
        
        item = items[0]
        item['chat_history'].append({
            "question": question,
            "answer": answer
        })
        self.db.put_item(Item=item)

    def get_chat_history(self):
        response = self.db.query(key_condition_expression=boto3.dynamodb.conditions.Key('connectionid').eq(self.connectionid))
        items = response.get('Items', None)
        if items is None or len(items) == 0:
            return None
        return items[0].get('chat_history', [])

    def remove_chat_history(self):
        self.db.delete_item(
            Key={
                'connectionid': self.connectionid
            }
        )