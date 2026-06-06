#!/usr/bin/env bash
# ==========================================================================================
# Fiddy: AI-Powered Alcohol Label Verification App
# startup.sh
#
# Purpose:
#   Starts the Fiddy Streamlit application inside a local or Azure-hosted container. The script
#   normalizes PORT and Streamlit server settings so the app listens on the container port
#   configured by Azure Container Apps or Azure App Service.
# ==========================================================================================

set -euo pipefail

APP_FILE="${APP_FILE:-app.py}"
PORT="${PORT:-${STREAMLIT_SERVER_PORT:-8501}}"
STREAMLIT_SERVER_ADDRESS="${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}"

export PORT
export STREAMLIT_SERVER_PORT="${PORT}"
export STREAMLIT_SERVER_ADDRESS
export STREAMLIT_BROWSER_GATHER_USAGE_STATS="${STREAMLIT_BROWSER_GATHER_USAGE_STATS:-false}"
export REQUIRE_LOCAL_OCR="${REQUIRE_LOCAL_OCR:-true}"
export ALLOW_EXTERNAL_ML_ENDPOINTS="${ALLOW_EXTERNAL_ML_ENDPOINTS:-false}"
export ENABLE_UPLOAD_PERSISTENCE="${ENABLE_UPLOAD_PERSISTENCE:-false}"
export ENABLE_RAW_TEXT_LOGGING="${ENABLE_RAW_TEXT_LOGGING:-false}"
export ENABLE_FILE_PATH_LOGGING="${ENABLE_FILE_PATH_LOGGING:-false}"

mkdir -p logging samples/labels samples/manifests

echo "Starting Fiddy Streamlit app."
echo "App file: ${APP_FILE}"
echo "Server address: ${STREAMLIT_SERVER_ADDRESS}"
echo "Port: ${PORT}"
echo "Local OCR required: ${REQUIRE_LOCAL_OCR}"
echo "External ML endpoints allowed: ${ALLOW_EXTERNAL_ML_ENDPOINTS}"

exec streamlit run "${APP_FILE}" \
	--server.address="${STREAMLIT_SERVER_ADDRESS}" \
	--server.port="${PORT}" \
	--server.headless=true \
	--browser.gatherUsageStats=false