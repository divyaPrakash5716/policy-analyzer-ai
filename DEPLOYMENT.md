# Policy Analyzer AI - Deployment Guide

## 🚀 Deployment Options

### Option 1: Netlify (Frontend) + Hugging Face Spaces (Backend)

#### Frontend (Netlify)
1. Push your code to GitHub.
2. Log in to Netlify and select **"Add new site"** > **"Import an existing project"**.
3. Connect your GitHub repository.
4. Set the base directory to `frontend`.
5. Netlify will autodetect Next.js. In **Site settings** > **Environment variables**, set:
   ```
   NEXT_PUBLIC_API_URL=https://your-hf-space-id.hf.space
   ```
6. Deploy.

#### Backend (Hugging Face Spaces)
1. Create a new Space on Hugging Face.
2. Select **Docker** as the SDK.
3. Choose the **"Blank"** template or upload the files.
4. In the Space **Settings** > **Variables and secrets**, add:
   ```
   GROQ_API_KEY=your_key
   TAVILY_API_KEY=your_key
   NOMIC_API_KEY=your_key
   REDIS_URL=your_upstash_redis_url
   ALLOWED_ORIGINS=https://your-netlify-app.netlify.app
   ```
5. The `Dockerfile` provided in the `/backend` folder will automatically configure the environment.

---

### Option 2: Vercel (Frontend) + Railway/Render (Backend)

#### Frontend (Vercel)
1. Push code to GitHub.
2. Connect repo to Vercel and set root directory to `frontend`.
3. Set environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
   ```
4. Deploy.

#### Backend (Railway/Render)
1. Connect repo to Railway/Render.
2. Set root directory to `backend`.
3. Set environment variables (same as HF Spaces above).
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## 🏗️ Redis Persistence (Upstash)
Since both HF Spaces and Netlify use ephemeral storage, you MUST use an external Redis for history persistence:
1. Create a free account at [Upstash](https://upstash.com/).
2. Create a new Redis database.
3. Copy the **Global Connect String** (starts with `redis://`).
4. Set this as `REDIS_URL` in your backend environment variables.

---

## 🔐 Environment Variables Summary

### Backend
| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Groq API key for LLM |
| `TAVILY_API_KEY` | ✅ | Tavily API for web search |
| `NOMIC_API_KEY` | ✅ | Nomic embeddings |
| `REDIS_URL` | ✅ | Redis URL (e.g., Upstash) |
| `ALLOWED_ORIGINS` | ✅ | Comma-separated frontend URLs |

### Frontend
| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | ✅ | Backend API URL |

---

## 🧪 Testing Production Build Locally

### Frontend
```bash
cd frontend
npm run build
npm start
```

### Backend
```bash
cd backend
# With Docker
docker build -t policy-backend .
docker run -p 8000:7860 -e REDIS_URL=... policy-backend
```
