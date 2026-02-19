# Policy Analyser AI

A comprehensive Policy Analysis system using Agentic RAG, featuring:
- **Comparator Agent**: Compare Regulatory vs Company Policies.
- **Policy Analyser**: Analyze individual policies.
- **Web Agent**: Search the web for context.
- **Coordinator**: Intelligently routes requests.

## Architecture
- **Frontend**: Next.js (Vercel)
- **Backend**: FastAPI + LangGraph (Hugging Face Spaces)

## Setup
### Backend
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
