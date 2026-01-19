# Policy Analyzer AI - Deployment Guide

## 🚀 Deployment Options

### Option 1: Vercel (Frontend) + Railway/Render (Backend)

#### Frontend (Vercel)
1. Push code to GitHub
2. Connect repo to Vercel
3. Set environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
   ```
4. Deploy

#### Backend (Railway/Render)
1. Connect repo to Railway/Render
2. Set root directory to `/backend`
3. Set environment variables:
   ```
   GROQ_API_KEY=your_key
   TAVILY_API_KEY=your_key
   NOMIC_API_KEY=your_key
   ALLOWED_ORIGINS=https://your-frontend.vercel.app
   ```
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

---

### Option 2: Hugging Face Spaces (Backend) + Vercel (Frontend)

#### Backend (HF Spaces)
1. Create new Space (Docker SDK)
2. Add `Dockerfile`:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY backend/requirements.txt .
   RUN pip install -r requirements.txt
   COPY backend/ .
   EXPOSE 7860
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
   ```
3. Set Secrets in Space settings

---

## 🔐 Environment Variables

### Backend (.env)
| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Groq API key for LLM |
| `TAVILY_API_KEY` | ✅ | Tavily API for web search |
| `NOMIC_API_KEY` | ✅ | Nomic embeddings |
| `ALLOWED_ORIGINS` | ✅ | Comma-separated frontend URLs |

### Frontend (.env.local)
| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | ✅ | Backend API URL |

---

## ⚠️ Pre-Deployment Checklist

- [ ] Remove/rotate any exposed API keys
- [ ] Set `ALLOWED_ORIGINS` to your frontend domain only
- [ ] Test file upload size limits
- [ ] Set up error monitoring (Sentry)
- [ ] Configure rate limiting
- [ ] Add health check endpoint
- [ ] Set up logging

---

## 🧪 Testing Production Build

### Frontend
```bash
cd frontend
npm run build
npm start
```

### Backend
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```
