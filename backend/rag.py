import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_chroma import Chroma
from langchain_nomic.embeddings import NomicEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class RAGSystem:
    def __init__(self, persist_directory="./chroma_db", embedding_model="nomic-embed-text-v1.5"):
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        # Initialize Embeddings
        self.embeddings = NomicEmbeddings(model=self.embedding_model, inference_mode="remote", nomic_api_key=os.getenv("NOMIC_API_KEY"))
    
    def ingest_documents(self, file_paths: List[str], collection_name: str) -> bool:
        """Ingests a list of files into the vector store."""
        all_docs = []
        for file_path in file_paths:
            if file_path.endswith(".pdf"):
                loader = PyPDFLoader(file_path)
            else:
                loader = TextLoader(file_path)
            all_docs.extend(loader.load())
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(all_docs)
        
        # Vector Store Ingestion
        try:
            Chroma.from_documents(
                documents=splits, 
                embedding=self.embeddings, 
                collection_name=collection_name,
                persist_directory=self.persist_directory
            )
            return True
        except Exception as e:
            print(f"Error ingesting documents: {e}")
            return False

    def get_retriever(self, collection_name: str):
        """Returns a hybrid retriever (Vector + BM25)."""
        # 1. Vector Retriever
        vectorstore = Chroma(
            collection_name=collection_name, 
            embedding=self.embeddings, 
            persist_directory=self.persist_directory
        )
        vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
        
        # 2. BM25 Retriever
        # Fetch all docs from vectorstore to build BM25 index (Simple approach for MVP)
        # In a real large app, we'd maintain a separate index or cache.
        docs = vectorstore.get()['documents'] 
        meta = vectorstore.get()['metadatas']
        # Reconstruct documents for BM25
        bm25_docs = [Document(page_content=d, metadata=m) for d, m in zip(docs, meta)]
        
        if not bm25_docs:
             # Fallback if empty
            return vector_retriever

        bm25_retriever = BM25Retriever.from_documents(bm25_docs)
        bm25_retriever.k = 5
        
        # 3. Ensemble
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever],
            weights=[0.5, 0.5]
        )
        
        return ensemble_retriever
