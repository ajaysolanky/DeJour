import os, sys
import tiktoken

class HiddenPrints:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout

class TokenCountCalculator:
    ENCODING_TYPE = "gpt2"  # encoding for text-davinci-003
    
    def __init__(self):
        self.encoding = tiktoken.get_encoding(self.ENCODING_TYPE)
    
    def get_num_tokens(self, text):
        return len(self.encoding.encode(text))
