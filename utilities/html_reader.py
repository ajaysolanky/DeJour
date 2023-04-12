import logging
from langchain import OpenAI, VectorDBQA
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import BSHTMLLoader
from langchain.prompts import PromptTemplate

class HTMLReader:
    def __init__(self):
        doc_loader = BSHTMLLoader('/Users/aalhadpatankar/Documents/Projects/DeJour/utilities/article.html')
        documents = doc_loader.load()
        text_splitter = CharacterTextSplitter(chunk_overlap=0, chunk_size=1000)
        texts = text_splitter.split_documents(documents)
        embeddings = OpenAIEmbeddings()
        docsearch = Chroma.from_documents(texts, embeddings)
        llm = OpenAI(model_name='gpt-4', temperature=0)
        qa_chain = VectorDBQA.from_chain_type(llm=llm, chain_type='stuff', vectorstore=docsearch)

        answer = qa_chain.run('What are the two guidelines?')      
        logging.info(answer) 