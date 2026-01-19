from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
import shutil
from dotenv import load_dotenv
from rag import RAGSystem
from graph import app as graph_app

load_dotenv()

app = FastAPI(
    title="Policy Analyser AI",
    docs_url=None,        # Disables /docs (Swagger UI)
    redoc_url=None,       # Disables /redoc (ReDoc)
    openapi_url=None      # Disables /openapi.json
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG
# Ensure ./chroma_db exists or will be created
rag = RAGSystem()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Policy Analyser AI Backend Running"}

@app.post("/upload")
async def upload_documents(
    regulatory_doc: Optional[UploadFile] = File(None),
    company_policy: Optional[UploadFile] = File(None)
):
    """
    Uploads documents and ingests them into respective collections.
    """
    statuses = {}
    
    if regulatory_doc:
        reg_path = os.path.join(UPLOAD_DIR, regulatory_doc.filename)
        with open(reg_path, "wb") as buffer:
            shutil.copyfileobj(regulatory_doc.file, buffer)
        
        success = rag.ingest_documents([reg_path], "regulatory_policy")
        statuses["regulatory"] = "ingested" if success else "failed"
        
    if company_policy:
        comp_path = os.path.join(UPLOAD_DIR, company_policy.filename)
        with open(comp_path, "wb") as buffer:
            shutil.copyfileobj(company_policy.file, buffer)
            
        success = rag.ingest_documents([comp_path], "company_policy")
        statuses["company"] = "ingested" if success else "failed"
        
    return {"status": statuses}

@app.post("/chat")
async def chat_endpoint(
    message: str = Form(...),
    policy_type: str = Form(...) # 'regulatory', 'company', 'both', 'none'
):
    """
    Invokes the agent graph.
    """
    # retrieve documents based on policy_type
    retrieved_docs = []
    
    if policy_type in ["company", "both"]:
        # Retrieve from company policy
        retriever = rag.get_retriever("company_policy")
        docs = retriever.invoke(message)
        retrieved_docs.extend([d.page_content for d in docs])

    if policy_type in ["both", "regulatory"]:
         # Retrieve from regulatory policy
        retriever = rag.get_retriever("regulatory_policy")
        docs = retriever.invoke(message)
        retrieved_docs.extend([d.page_content for d in docs])
    
    # Run Graph
    inputs = {
        "messages": [("user", message)],
        "policy_type": policy_type,
        "query": message,
        "documents": retrieved_docs
    }
    
    try:
        result = graph_app.invoke(inputs)
        # Result is the final state. Get the last message.
        last_message = result["messages"][-1]
        response_text = last_message.content if hasattr(last_message, 'content') else str(last_message)
        
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
