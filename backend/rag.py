import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from flashrank import Ranker, RerankRequest

class HybridRetriever:
    """Wrapper class for hybrid retrieval combining BM25 and vector search with FlashRank reranking."""
    def __init__(self, vector_retriever, bm25_retriever):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        # Initialize FlashRank reranker
        self.ranker = Ranker()
    
    def invoke(self, query: str):
        """Retrieve documents using both retrievers, combine, and rerank."""
        vector_results = self.vector_retriever.invoke(query)
        bm25_results = self.bm25_retriever.invoke(query)
        
        # Combine results (simple union, avoiding duplicates by content)
        combined_dict = {doc.page_content: doc for doc in vector_results + bm25_results}
        combined_docs = list(combined_dict.values())
        
        if not combined_docs:
            return []

        # Prepare for FlashRank
        # FlashRank expects list of dicts: [{"id": 1, "text": "...", "meta": {...}}, ...]
        passages = [
            {"id": i, "text": doc.page_content, "meta": doc.metadata}
            for i, doc in enumerate(combined_docs)
        ]
        
        rerankrequest = RerankRequest(query=query, passages=passages)
        results = self.ranker.rerank(rerankrequest)
        
        # Convert back to LangChain Documents, keeping top 5
        reranked_docs = [
            Document(page_content=r['text'], metadata=r['meta'])
            for r in results[:5]
        ]
        
        return reranked_docs
    
    def get_relevant_documents(self, query: str):
        """Alias for invoke to match retriever interface."""
        return self.invoke(query)

class RAGSystem:
    def __init__(self, persist_directory="./chroma_db", embedding_model="nomic-embed-text-v1.5"):
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        # Initialize Embeddings
        # Initialize Embeddings using HuggingFace implementation of Nomic model
        # This avoids the Nomic API key authentication issue and works with the provided HF token
        print(f"DEBUG: Initializing HuggingFaceEmbeddings with model: {self.embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=f"nomic-ai/{self.embedding_model}",
            model_kwargs={"trust_remote_code": True}
        )
    
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
