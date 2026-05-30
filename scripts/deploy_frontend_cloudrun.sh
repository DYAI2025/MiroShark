#!/usr/bin/env bash
# Deploy MiroShark frontend to Google Cloud Run (europe-west1, project: bazodiac)
set -euo pipefail

PROJECT="bazodiac"
REGION="europe-west1"
SERVICE="miroshark-frontend"
REPO="${REGION}-docker.pkg.dev/${PROJECT}/cloud-run-source-deploy"
IMAGE="${REPO}/${SERVICE}"
TAG="${1:-latest}"

VITE_API_BASE_URL="https://miroshark-api-zul335dpla-ew.a.run.app"
VITE_INTERNAL_KEY="92e02ff085d259acc41d9958d78acddd6f60af74fadbee56f7f4ac344df09a21"

echo "==> Building and pushing ${IMAGE}:${TAG}"
gcloud builds submit \
  --project="${PROJECT}" \
  --config=cloudbuild.frontend.yaml \
  --substitutions="_IMAGE=${IMAGE}:${TAG},_VITE_API_BASE_URL=${VITE_API_BASE_URL},_VITE_INTERNAL_KEY=${VITE_INTERNAL_KEY}" \
  .

echo "==> Deploying ${SERVICE} to Cloud Run"
gcloud run deploy "${SERVICE}" \
  --project="${PROJECT}" \
  --region="${REGION}" \
  --image="${IMAGE}:${TAG}" \
  --port=8080 \
  --memory=256Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --timeout=30 \
  --concurrency=80 \
  --allow-unauthenticated

echo "==> Done. Service URL:"
gcloud run services describe "${SERVICE}" \
  --project="${PROJECT}" \
  --region="${REGION}" \
  --format="value(status.url)"
