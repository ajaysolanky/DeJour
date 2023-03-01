from langchain.embeddings import OpenAIEmbeddings
from typing import Any, Dict, List, Optional

# class EmbeddingsModel(OpenAIEmbeddings):
#     EMBEDDING_ENGINE = 'text-embedding-ada-002'

#     def __init__(self) -> None:
#         super().__init__()

#     def embed_documents(self, texts: List[str]) -> List[List[float]]:
#         """Call out to OpenAI's embedding endpoint for embedding search docs.
#         Args:
#             texts: The list of texts to embed.
#         Returns:
#             List of embeddings, one for each text.
#         """
#         responses = [
#             self._embedding_func(text, engine=self.EMBEDDING_ENGINE)
#             for text in texts
#         ]
#         return responses
    
#     def embed_query(self, text: str) -> List[float]:
#         """Call out to OpenAI's embedding endpoint for embedding query text.
#         Args:
#             text: The text to embed.
#         Returns:
#             Embeddings for the text.
#         """
#         embedding = self._embedding_func(
#             text, engine=self.EMBEDDING_ENGINE
#         )
#         return embedding