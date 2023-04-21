from abc import ABC, abstractmethod

class WeaviateClass(ABC):
    def __init__(self, publisher_str) -> None:
        self.class_name = self.get_full_class_name(publisher_str)

    @abstractmethod
    def get_full_class_name(self, publisher):
        pass

    @property
    def text_field_name(self):
        raise NotImplementedError()

    @abstractmethod
    def get_class_obj(self):
        pass

class WeaviateClassArticleSnippet(WeaviateClass):
    def get_full_class_name(self, publisher_str):
        return f"ArticleSnippet_{publisher_str}"

    @property
    def text_field_name(self):
        return "snippet"

    def get_class_obj(self):
        return {
            "class": self.class_name,
            "description": "Snippet of text spliced from an article",
            "vectorizer": "text2vec-openai",
            "moduleConfig": {
                "text2vec-openai": {
                    "vectorizeClassName": True
                }
            },
            "properties": [
                {
                    "name": "title",
                    "description": "The title",
                    "dataType": ["text"],
                },
                {
                    "name": "source",
                    "description": "URL of article",
                    "dataType": ["text"],
                },
                {
                    "name": "fetch_timestamp",
                    "description": "Timestamp of when the article was fetched",
                    "dataType": ["date"],
                },
                {
                    "name": "publish_timestamp",
                    "description": "Timestamp of when the article was published",
                    "dataType": ["date"],
                },
                {
                    "name": "top_image_url",
                    "description": "URL of the top image from the article",
                    "dataType": ["text"],
                },
                {
                    "name": self.text_field_name,
                    "description": "The actual snippet",
                    "dataType": ["text"],
                },
            ]
        }
    
class WeaviateClassBookSnippet(WeaviateClass):
    def get_full_class_name(self, publisher_str):
        return f"BookSnippet_{publisher_str}"

    @property
    def text_field_name(self):
        return "snippet"

    def get_class_obj(self):
        return {
            "class": self.class_name,
            "description": "Snippet of text spliced from a passage of a book",
            "vectorizer": "text2vec-openai",
            "moduleConfig": {
                "text2vec-openai": {
                    "vectorizeClassName": True
                }
            },
            "properties": [
                {
                    "name": "source",
                    "description": "Start and end indices of the text",
                    "dataType": ["text"],
                },
                {
                    "name": self.text_field_name,
                    "description": "The actual snippet",
                    "dataType": ["text"],
                },
            ]
        }