<<<<<<< HEAD
# ⚡ CareerForge — AI Career Coach

> **Talk to Forge, your AI career counselor.** Upload your resume, have a natural voice conversation, and get a personalised career roadmap with real-time job market data — all in minutes.

Built for the [Gemini Live Agent Challenge](https://geminiliveagentchallenge.devpost.com/) 🏆

---

## 🎯 What It Does

CareerForge is a **voice-first AI career coaching agent** that:

1. **📄 Analyzes your resume** using Gemini vision (PDF/image upload)
2. **🎙️ Conducts a live voice interview** via the Gemini Live API — natural, interruptible conversation
3. **🔍 Researches the live job market** using Google Search grounding for real-time salary data, demand trends, and employer insights
4. **📊 Identifies your skill gaps** against target role requirements with personalised prioritisation
5. **🗺️ Builds a personalised career roadmap** that adapts to your burnout level, risk tolerance, finances, and timeline
6. **📥 Generates a professional PDF report** — a take-home career plan

## ✨ Key Features

| Feature | Technology |
|---|---|
| **Live Voice AI** | Gemini Live API (bidi streaming, native audio) |
| **Multi-Agent Architecture** | Google ADK with 4 specialised agents |
| **Real-Time Market Data** | Google Search grounding |
| **Resume Vision Analysis** | Gemini multimodal (PDF/image) |
| **Emotionally Adaptive** | Burnout/confidence/risk-aware coaching |
| **PDF Career Reports** | ReportLab with branded styling |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                  │
│  Landing → Onboarding → Live Voice Session → Report        │
│  - WebSocket audio streaming (PCM 16kHz)                   │
│  - AudioWorklet for mic capture                            │
│  - AudioBufferSourceNode queue for playback                │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP REST + WebSocket
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               BACKEND (FastAPI on Cloud Run)                │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │   /profile   │  │  /ws/live/   │  │ /generate-report  │  │
│  │ /upload-res. │  │  bidi audio  │  │  post-session     │  │
│  │   /chat      │  │  streaming   │  │  PDF pipeline     │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
│                                                             │
│  ┌─────────────────── ADK Agents ────────────────────────┐  │
│  │                                                        │  │
│  │  forge (text)          forge_live (audio)              │  │
│  │    ├─ resume_analyst     (native audio model)         │  │
│  │    ├─ market_researcher                                │  │
│  │    └─ career_planner   report_generator               │  │
│  │                          (all tools, no sub-agents)   │  │
│  └────────────────────────────────────────────────────────┘  │
│                         │                                    │
└─────────────────────────┼────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌────────────┐  ┌────────────┐  ┌────────────┐
   │ Gemini API │  │  Gemini    │  │  Google    │
   │ (Live API  │  │ 2.5 Flash  │  │  Search   │
   │  native    │  │ (tools,    │  │ Grounding │
   │  audio)    │  │  vision)   │  │           │
   └────────────┘  └────────────┘  └────────────┘
```

### Google Cloud Services Used
- **Cloud Run** — Backend API hosting (FastAPI + WebSocket)
- **Cloud Run** — Frontend hosting (nginx + static React build)
- **Gemini API** — Live API (native audio), 2.5 Flash (text/vision), Google Search grounding

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 18+
- Google API Key from [AI Studio](https://aistudio.google.com/apikey)

### Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp career_counselor_agent/.env.example career_counselor_agent/.env
# Edit .env and add your GOOGLE_API_KEY

# Run the server
uvicorn career_counselor_agent.api.server:app --reload --port 8000
```

### Frontend Setup
```bash
cd careerforge-frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Visit `http://localhost:5173` and start your career coaching session!

## ☁️ Cloud Deployment (Google Cloud Run)

### Automated Deployment
```bash
# Set your API key
export GOOGLE_API_KEY=your_key_here

# Deploy everything with one command
chmod +x deploy.sh
./deploy.sh YOUR_GCP_PROJECT_ID us-central1
```

### Manual Deployment
```bash
# Deploy backend
cd backend
gcloud run deploy careerforge-backend \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars "GOOGLE_API_KEY=$GOOGLE_API_KEY,GOOGLE_GENAI_USE_VERTEXAI=FALSE" \
    --memory 1Gi --timeout 300 --session-affinity

# Get backend URL
BACKEND_URL=$(gcloud run services describe careerforge-backend --region us-central1 --format 'value(status.url)')

# Deploy frontend
cd ../careerforge-frontend
gcloud run deploy careerforge-frontend \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --build-arg "VITE_API_URL=$BACKEND_URL"

# Update backend CORS
gcloud run services update careerforge-backend \
    --region us-central1 \
    --update-env-vars "FRONTEND_URL=$(gcloud run services describe careerforge-frontend --region us-central1 --format 'value(status.url)')"
```

## 🧪 Tech Stack

| Layer | Technology |
|---|---|
| **AI Framework** | Google ADK (Agent Development Kit) |
| **AI Models** | Gemini 2.5 Flash, Gemini 2.5 Flash Native Audio |
| **AI SDK** | Google GenAI Python SDK |
| **Backend** | FastAPI, uvicorn, WebSockets |
| **Frontend** | React 19, TypeScript, Vite |
| **UI** | Framer Motion, Lucide Icons |
| **PDF** | ReportLab |
| **Cloud** | Google Cloud Run |
| **Grounding** | Google Search (real-time job market data) |

## 📁 Project Structure

```
geminiagentchallenge/
├── backend/
│   ├── career_counselor_agent/
│   │   ├── agent.py           # ADK agent definitions (forge, forge_live, report_generator)
│   │   ├── api/server.py      # FastAPI server (REST + WebSocket)
│   │   ├── config.py          # Environment/API key setup
│   │   ├── models.py          # User profile models
│   │   ├── prompts/           # System instructions
│   │   └── tools/             # Agent tools
│   │       ├── resume.py      # Resume analysis (text + vision)
│   │       ├── search_market.py  # Job market research (Google Search grounding)
│   │       ├── skill_gap.py   # Skill gap analysis
│   │       ├── roadmap.py     # Career roadmap generation
│   │       ├── courses.py     # Course recommendations
│   │       └── pdf_generator.py  # PDF report generation
│   ├── Dockerfile
│   └── requirements.txt
├── careerforge-frontend/
│   ├── src/
│   │   ├── pages/             # Landing, Onboarding, Live Session, Report
│   │   ├── hooks/             # useLiveAgent (bidi audio streaming)
│   │   └── services/api.ts    # Backend API client
│   └── Dockerfile
├── deploy.sh                  # Automated GCP deployment script
└── README.md
```

## 👥 Team

Built with ❤️ for the Gemini Live Agent Challenge

## 📝 License

MIT
=======
# careerforge_live
>>>>>>> c67d1dfad7c4e9f623a40d4d39e297199d13e947
