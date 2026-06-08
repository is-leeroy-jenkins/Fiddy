# ==========================================================================================
# Fiddy: AI-Powered Alcohol Label Verification App
# Dockerfile
#
# Purpose:
#   Builds an Azure-compatible Streamlit container for Fiddy. The image includes Python,
#   Streamlit runtime dependencies, local Tesseract OCR, Poppler PDF tooling, OpenCV-compatible
#   system libraries, non-root execution, local no-external-ML defaults, no-persistence defaults,
#   writable runtime folders, and a Streamlit health check.
#
# Requirements:
#   - app.py must exist at the repository root.
#   - startup.sh must exist at the repository root.
#   - requirements.txt must exist at the repository root.
#   - Runtime Python modules imported as src.* must exist under /app/src.
#
# Returns:
#   A runnable container image suitable for local Docker, Azure Container Apps, or Azure App
#   Service for Containers.
# ==========================================================================================

FROM python:3.11-slim-bookworm

# ==========================================================================================
# Environment
# ==========================================================================================

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

ENV APP_FILE=app.py
ENV PORT=8501
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

ENV DEPLOYMENT_TARGET=azure
ENV ENABLE_AZURE_DEPLOYMENT_MODE=true
ENV AZURE_READY_ARTIFACTS_PRESENT=true
ENV AZURE_SMOKE_TEST_PASSED=false

ENV REQUIRE_LOCAL_OCR=true
ENV ALLOW_EXTERNAL_ML_ENDPOINTS=false
ENV ENABLE_AZURE_VISION=false
ENV COLA_INTEGRATION_ENABLED=false

ENV NO_PERSISTENCE_MODE=true
ENV LONG_TERM_STORAGE_DISABLED=true
ENV ENABLE_UPLOAD_PERSISTENCE=false
ENV ENABLE_TEMP_CLEANUP=true

ENV ENABLE_RAW_TEXT_LOGGING=false
ENV ENABLE_MANIFEST_ROW_LOGGING=false
ENV ENABLE_FILE_PATH_LOGGING=false
ENV ENABLE_FILE_PATH_EXPORT=false
ENV ENABLE_RAW_OCR_EXPORT=false
ENV ENABLE_EXTRACTED_DATA_EXPORT=false
ENV ENABLE_REDACTED_EVIDENCE_EXPORT=true
ENV ENABLE_UNREDACTED_ACCEPTANCE_PACKAGE=false

ENV MAX_BATCH_FILES=50
ENV MAX_PARALLEL_WORKERS=4
ENV LABEL_PROCESSING_SLA_SECONDS=5
ENV BATCH_ACCEPTANCE_MIN_FILES=20
ENV BATCH_ACCEPTANCE_MAX_FILES=50
ENV BATCH_ACCEPTANCE_MAX_AVERAGE_SECONDS=5
ENV BATCH_ACCEPTANCE_MAX_P95_SECONDS=5
ENV BATCH_ACCEPTANCE_MAX_BREACH_RATE=0

ENV OCR_ENGINE=tesseract
ENV OCR_LANGUAGE=eng
ENV OCR_TIMEOUT_SECONDS=5
ENV OCR_MINIMUM_WIDTH=800
ENV OCR_MINIMUM_HEIGHT=800
ENV MAX_IMAGE_DIMENSION=2400
ENV MAX_PDF_PAGES=1

ENV LOG_DIR=/app/logging
ENV LOG_PATH=/app/logging/Exceptions.db
ENV LOG_FILE=Exceptions

# ==========================================================================================
# Working Directory
# ==========================================================================================

WORKDIR /app

# ==========================================================================================
# System Dependencies
# ==========================================================================================

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		bash \
		ca-certificates \
		curl \
		tesseract-ocr \
		tesseract-ocr-eng \
		poppler-utils \
		libglib2.0-0 \
		libgl1 \
		libsm6 \
		libxext6 \
		libxrender1 \
		libgomp1 \
	&& rm -rf /var/lib/apt/lists/*

# ==========================================================================================
# Python Dependencies
# ==========================================================================================

COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel \
	&& python -m pip install --no-cache-dir -r /app/requirements.txt

# ==========================================================================================
# Application Files
# ==========================================================================================

COPY . /app

# ==========================================================================================
# Runtime User and Writable Directories
# ==========================================================================================

RUN useradd --create-home --shell /bin/bash fiddy \
	&& mkdir -p /app/logging /app/samples/labels /app/samples/manifests /app/.streamlit \
	&& chmod +x /app/startup.sh \
	&& chown -R fiddy:fiddy /app

USER fiddy

# ==========================================================================================
# Network and Health Check
# ==========================================================================================

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
	CMD curl --fail "http://127.0.0.1:${PORT}/_stcore/health" || exit 1

# ==========================================================================================
# Startup
# ==========================================================================================

CMD ["/app/startup.sh"]