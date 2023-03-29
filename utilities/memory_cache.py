class ChatHistoryMemoryService:
    def __init__(self):
        self.question_answer_pairs = {}

    def add_object_if_needed(self, session_id, question, answer):
        existing_history = self.question_answer_pairs.get(session_id, None)
        if existing_history is None:
            self.question_answer_pairs[session_id] = [(question, answer)]
        else:
            self.question_answer_pairs[session_id] = existing_history + [(question, answer)]

    def get_chat_history(self, session_id):
        return self.question_answer_pairs.get(session_id, [])
    
    def print_contents(self):
        print(self.question_answer_pairs)