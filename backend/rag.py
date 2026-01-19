import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_chroma import Chroma
from langchain_nomic.embeddings import NomicEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class HybridRetriever:
    """Wrapper class for hybrid retrieval combining BM25 and vector search."""
    def __init__(self, vector_retriever, bm25_retriever):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
    
    def invoke(self, query: str):
        """Retrieve documents using both retrievers and combine results."""
        vector_results = self.vector_retriever.invoke(query)
        bm25_results = self.bm25_retriever.invoke(query)
        
        # Combine results (simple union, avoiding duplicates by content)
        combined_results = {doc.page_content: doc for doc in vector_results + bm25_results}
        return list(combined_results.values())
    
    def get_relevant_documents(self, query: str):
        """Alias for invoke to match retriever interface."""
        return self.invoke(query)

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
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )
        vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
        
        # 2. BM25 Retriever
        docs = vectorstore.get()['documents'] 
        meta = vectorstore.get()['metadatas']
        bm25_docs = [Document(page_content=d, metadata=m) for d, m in zip(docs, meta)]
        
        if not bm25_docs:
            # Fallback if empty
            return vector_retriever

        bm25_retriever = BM25Retriever.from_documents(bm25_docs)
        bm25_retriever.k = 5
        
        # 3. Return Hybrid Retriever
        return HybridRetriever(vector_retriever, bm25_retriever)
