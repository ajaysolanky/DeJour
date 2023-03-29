import sqlite3

class ChatHistoryService:
    FILE_NAME = "chat_history.db"
    def __init__(self):
        self.db_connection = sqlite3.connect(self.FILE_NAME)
        self.create_table_if_needed()

    def create_table_if_needed(self):
        create_table = '''CREATE TABLE IF NOT EXISTS chat_history (
            session_id VARCHAR(255) PRIMARY KEY,
            chat_history TEXT NOT NULL
        );'''
        cursor = self.db_connection.cursor()
        cursor.execute(create_table)
        self.db_connection.commit()

    def add_object_if_needed(self, session_id, chat_history):
        existing = self.get_chat_history(session_id)
        if existing is None:
            print("here!")
            self.add_object(session_id, chat_history)
        else:
            print("here 2!")
            self.update_object(session_id, chat_history)

    def update_object(self, session_id, chat_history):
        write_query = '''UPDATE chat_history SET chat_history = ? WHERE session_id = ?;'''
        cursor = self.db_connection.cursor()
        cursor.execute(write_query, ( chat_history, session_id))
        self.db_connection.commit()

    def add_object(self, session_id, chat_history):
        write_query = ''' INSERT INTO chat_history (session_id, chat_history)
VALUES(?, ?);'''
        cursor = self.db_connection.cursor()
        cursor.execute(write_query, (session_id, chat_history))
        self.db_connection.commit()

    def get_chat_history(self, session_id):
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT * FROM chat_history WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        # TODO: Would be better with a named dict instead of relying on index of column
        return row[1]
    
    def print_contents(self):
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT * FROM chat_history")
        rows = cursor.fetchall()
        for row in rows:
            print(row)

