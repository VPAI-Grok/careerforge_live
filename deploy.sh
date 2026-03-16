#!/bin/bash
# ── CareerForge — Automated Cloud Deployment Script ───────────────────────────
# Deploys CareerForge backend + frontend to Google Cloud Run.
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - A GCP project with billing enabled
#   - GOOGLE_API_KEY env var set (from Google AI Studio)
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh <PROJECT_ID> [REGION]
#
# Example:
#   GOOGLE_API_KEY=AIza... ./deploy.sh my-careerforge-project us-central1
#
# Created for automated deployment (Gemini Live Agent Challenge bonus points)
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Arguments ─────────────────────────────────────────────────────────────────
PROJECT_ID="${1:?Usage: ./deploy.sh <PROJECT_ID> [REGION]}"
REGION="${2:-us-central1}"
BACKEND_SERVICE="careerforge-backend"
FRONTEND_SERVICE="careerforge-frontend"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║         CareerForge — Cloud Deployment Script           ║"
echo "║                                                         ║"
echo "║  Project:  ${PROJECT_ID}"
echo "║  Region:   ${REGION}"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Validate ──────────────────────────────────────────────────────────────────
if [ -z "${GOOGLE_API_KEY:-}" ]; then
    echo "❌ GOOGLE_API_KEY is not set."
    echo "   export GOOGLE_API_KEY=your_key_here"
    exit 1
fi

# ── Step 1: Set project & enable APIs ─────────────────────────────────────────
echo "🔧 Setting project to ${PROJECT_ID}..."
gcloud config set project "${PROJECT_ID}"

echo "🔌 Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    --quiet

# ── Step 2: Deploy Backend ────────────────────────────────────────────────────
echo ""
echo "🚀 [1/3] Deploying backend to Cloud Run..."
gcloud run deploy "${BACKEND_SERVICE}" \
    --source ./backend \
    --region "${REGION}" \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY},GOOGLE_GENAI_USE_VERTEXAI=FALSE" \
    --memory 1Gi \
    --cpu 1 \
    --timeout 1200 \
    --session-affinity \
    --min-instances 0 \
    --max-instances 3 \
    --quiet

BACKEND_URL=$(gcloud run services describe "${BACKEND_SERVICE}" \
    --region "${REGION}" \
    --format 'value(status.url)')

echo "✅ Backend deployed: ${BACKEND_URL}"

# ── Step 3: Deploy Frontend ───────────────────────────────────────────────────
echo ""
echo "🚀 [2/3] Deploying frontend to Cloud Run..."
echo "   (baking in VITE_API_URL=${BACKEND_URL})"

gcloud run deploy "${FRONTEND_SERVICE}" \
    --source ./careerforge-frontend \
    --region "${REGION}" \
    --platform managed \
    --allow-unauthenticated \
    --build-arg "VITE_API_URL=${BACKEND_URL}" \
    --port 8080 \
    --memory 256Mi \
    --cpu 1 \
    --timeout 60 \
    --min-instances 0 \
    --max-instances 2 \
    --quiet

FRONTEND_URL=$(gcloud run services describe "${FRONTEND_SERVICE}" \
    --region "${REGION}" \
    --format 'value(status.url)')

echo "✅ Frontend deployed: ${FRONTEND_URL}"

# ── Step 4: Update Backend CORS ───────────────────────────────────────────────
echo ""
echo "🔧 [3/3] Updating backend CORS with frontend URL..."
gcloud run services update "${BACKEND_SERVICE}" \
    --region "${REGION}" \
    --update-env-vars "FRONTEND_URL=${FRONTEND_URL}" \
    --quiet

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              ✅  DEPLOYMENT COMPLETE!                   ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                         ║"
echo "║  🌐 Frontend:  ${FRONTEND_URL}"
echo "║  🔧 Backend:   ${BACKEND_URL}"
echo "║  💚 Health:    ${BACKEND_URL}/health"
echo "║                                                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
