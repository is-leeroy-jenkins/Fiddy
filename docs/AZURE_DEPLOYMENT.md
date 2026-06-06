# Fiddy Azure Deployment Guide

## Purpose

This guide explains how to run Fiddy as an Azure-compatible, local-OCR Streamlit prototype.

Fiddy is designed to avoid external OCR and external machine-learning endpoints during the
prototype. The container image installs Tesseract OCR and Poppler locally so image and PDF
processing can occur inside the deployed container.

## Recommended Deployment Target

The recommended prototype target is **Azure Container Apps**.

Azure Container Apps supports container ingress with a target port, and runtime environment
variables can be configured for the container app. Microsoft also documents `az containerapp up` as
a convenient deployment command that can create the Container Apps environment, Log Analytics
workspace, and container app deployment.

## Project Structure

Expected project structure:

```text
Fiddy/
├── app.py
├── config.py
├── booger.py
├── requirements.txt
├── Dockerfile
├── startup.sh
├── .dockerignore
├── docs/
│   └── AZURE_DEPLOYMENT.md
├── samples/
│   ├── labels/
│   └── manifests/
├── src/
│   ├── acceptance_checker.py
│   ├── accessibility_checklist.py
│   ├── batch_processor.py
│   ├── image_processor.py
│   ├── ocr_engine.py
│   ├── performance_monitor.py
│   └── ...
└── tests/
    └── __init__.py