# ==========================================================================================
# Fiddy: AI-Powered Alcohol Label Verification App
# Dockerfile
#
# Purpose:
#   Builds a local-OCR, Azure-compatible container image for the Fiddy Streamlit prototype.
#   The image installs Python dependencies, Tesseract OCR, English OCR data, and Poppler
#   utilities required by pdf2image. The container runs Streamlit on the PORT environment
#   variable so Azure Container Apps or Azure App Service can route traffic correctly.
# ==========================================================================================

FROM python:3.11-slim-bookworm

# ==========================================================================================
# Environment
# ==========================================================================================

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PORT=8501
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV OCR_ENGINE=tesseract
ENV OCR_LANGUAGE=eng
ENV REQUIRE_LOCAL_OCR=true
ENV ALLOW_EXTERNAL_ML_ENDPOINTS=false
ENV ENABLE_AZURE_DEPLOYMENT_MODE=true
ENV ENABLE_UPLOAD_PERSISTENCE=false
ENV ENABLE_RAW_TEXT_LOGGING=false
ENV ENABLE_FILE_PATH_LOGGING=false

# ==========================================================================================
# System Packages
# ==========================================================================================

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		tesseract-ocr \
		tesseract-ocr-eng \
		poppler-utils \
		libglib2.0-0 \
		libgl1 \
		libsm6 \
		libxext6 \
		libxrender1 \
		ca-certificates \
		curl \
		bash \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

# ==========================================================================================
# Application User and Working Directory
# ==========================================================================================

RUN useradd --create-home --shell /bin/bash fiddy

WORKDIR /app

# ==========================================================================================
# Python Dependencies
# ==========================================================================================

COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip \
	&& python -m pip install -r /app/requirements.txt

# ==========================================================================================
# Application Files
# ==========================================================================================

COPY . /app

RUN mkdir -p /app/logging /app/samples/labels /app/samples/manifests \
	&& chmod +x /app/startup.sh \
	&& chown -R fiddy:fiddy /app

USER fiddy

# ==========================================================================================
# Health and Runtime
# ==========================================================================================

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
	CMD curl --fail "http://127.0.0.1:${PORT}/_stcore/health" || exit 1

CMD [ "/app/startup.sh" ]