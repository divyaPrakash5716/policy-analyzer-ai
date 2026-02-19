import os
from typing import List, Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_core.documents import Document

class DocumentProcessor:
    @staticmethod
    def load_and_split(file_path: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap
        )
        splits = text_splitter.split_documents(docs)
        return splits

class VectorDB:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="nomic-ai/nomic-embed-text-v1.5",
            model_kwargs={"trust_remote_code": True}
        )
    
    def create_vector_store(self, documents: List[Document], collection_name: str):
        # Create a new vector store for the specific document (company or regulatory)
        # We use a unique collection name to separate them
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embedding_model,
            collection_name=collection_name,
            persist_directory=self.persist_directory
        )
        return vectorstore
    
    def get_retriever(self, vectorstore, k: int = 4):
        return vectorstore.as_retriever(search_kwargs={"k": k})

class HybridRetriever:
    def __init__(self, documents: List[Document], vectorstore):
        self.bm25_retriever = BM25Retriever.from_documents(documents)
        self.bm25_retriever.k = 4
        
        self.vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=[self.bm25_retriever, self.vector_retriever],
            weights=[0.5, 0.5]
        )
        
    def get_chain(self):
        return self.ensemble_retriever
