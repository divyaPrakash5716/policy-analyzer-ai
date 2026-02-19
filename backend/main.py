from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
import shutil
import pandas as pd
import mlflow
import mlflow.langchain
import mlflow.metrics.genai as genai_metrics
from dotenv import load_dotenv

# Load env vars before importing anything that uses them
# Try both local and backend/ path
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from rag import RAGSystem
from graph import app as graph_app
import mlflow
import mlflow.langchain
import mlflow.metrics.genai as genai_metrics

# Initialize MLflow - uses MLFLOW_TRACKING_URI env var (DagsHub in prod, localhost in dev)
mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(mlflow_uri)
mlflow.set_experiment("Policy Analyzer AI")

# DagsHub auth in production
if os.getenv("DAGSHUB_TOKEN"):
    os.environ["MLFLOW_TRACKING_USERNAME"] = os.getenv("MLFLOW_TRACKING_USERNAME", "divyaPrakash5716")
    os.environ["MLFLOW_TRACKING_PASSWORD"] = os.getenv("DAGSHUB_TOKEN")

try:
    mlflow.langchain.autolog()
except Exception as e:
    print(f"MLflow autolog skipped: {e}")

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
    policy_type: str = Form(...), # 'regulatory', 'company', 'both', 'none'
    session_id: Optional[str] = Form("default_session"),
    user_id: Optional[str] = Form("default_user")
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
        "documents": retrieved_docs,
        "user_id": user_id
    }
    
    try:
        # Configure thread_id for persistent memory
        config = {
            "configurable": {"thread_id": session_id}
        }
        
        result = graph_app.invoke(
            inputs,
            config=config
        )
        last_message = result["messages"][-1]
        response_text = last_message.content if hasattr(last_message, 'content') else str(last_message)
        
        # MLflow Evaluation - Only log if there's context and it's a policy query
        if policy_type != "web" and retrieved_docs:
            try:
                eval_df = pd.DataFrame([{
                    "query": message,
                    "response": response_text,
                    "context": "\n".join(retrieved_docs)
                }])
                
                # Set up Groq as an OpenAI-compatible judge for MLflow metrics
                os.environ["OPENAI_API_KEY"] = os.getenv("GROQ_API_KEY")
                os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"
                
                # Use Llama-3.1-8b-instant as the judge
                judge_model = "openai:/llama-3.1-8b-instant"
                
                faithfulness = genai_metrics.faithfulness(model=judge_model)
                relevance = genai_metrics.answer_relevance(model=judge_model)
                
                with mlflow.start_run(run_name=f"Eval_{session_id}", nested=True):
                    mlflow.evaluate(
                        data=eval_df,
                        targets="response",
                        model_type="question-answering",
                        evaluators="default",
                        extra_metrics=[faithfulness, relevance],
                        evaluator_config={
                            "col_mapping": {
                                "inputs": "query",
                                "context": "context"
                            }
                        }
                    )
            except Exception as eval_err:
                print(f"DEBUG: MLflow GenAI Evaluation failed: {eval_err}")

        return {
            "response": response_text,
            "alerts": result.get("alerts", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Use PORT environment variable if available, else default to 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
