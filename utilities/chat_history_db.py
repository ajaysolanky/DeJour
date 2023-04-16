import boto3
import logging

dynamodb = boto3.resource('dynamodb')
logging.getLogger().setLevel(logging.INFO)

class ChatHistoryDB: 
    TABLE_NAME = "dejour_chat_history"
    def __init__(self):
        self.table = dynamodb.Table(self.TABLE_NAME)

    def put_item(self, Item):
        self.table.put_item(Item=Item)

    def get_item(self, Key):
        self.table.get_item(Key=Key)

    def delete_item(self, Key):
        self.table.delete_item(Key=Key)

class InMemoryDB: 
    def __init__(self):
        self.db = {}

    def put_item(self, Item):
        print(Item)
        connection_id = Item["connectionid"]
        self.db[connection_id] = Item

    def get_item(self, Key):
        connection_id = Key["connectionid"]
        item = self.db.get(connection_id)
        print(item)
        return {
            "Item": item
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
        response = self.db.get_item(
            Key={
                'connectionid': self.connectionid
            }
        )
        item = response['Item']
        item['chat_history'].append({
            "question": question,
            "answer": answer
        })
        self.db.put_item(Item=item)

    def get_chat_history(self):
        response = self.db.get_item(
            Key={
                'connectionid': self.connectionid
            }
        )
        return response['Item']['chat_history']

    def remove_chat_history(self):
        self.db.delete_item(
            Key={
                'connectionid': self.connectionid
            }
        )