"""Configuration constants for the SAP AI Documentation Assistant UI."""

import os

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"
SERVICES_ENDPOINT = f"{API_BASE_URL}/api/v1/kb/services"
ASK_ENDPOINT = f"{API_BASE_URL}/api/v1/ask"

REQUEST_TIMEOUT = 30  # seconds

MAX_QUESTION_LENGTH = 2000

# Fallback display names when API is unavailable
SERVICE_DISPLAY = {
    "ai_core": "SAP AI Core",
    "genai_hub": "Generative AI Hub",
    "ai_launchpad": "SAP AI Launchpad",
    "joule": "SAP Joule",
    "hana_cloud_vector": "SAP HANA Cloud Vector Engine",
    "document_processing": "Document Information Extraction",
}

# Colors for service badges
SERVICE_COLORS = {
    "ai_core": "#0A6ED1",
    "genai_hub": "#E78C07",
    "ai_launchpad": "#1A9898",
    "joule": "#945ECF",
    "hana_cloud_vector": "#D04A02",
    "document_processing": "#188918",
}

DEFAULT_SERVICE_COLOR = "#6B7B8D"

SUGGESTED_QUESTIONS = [
    "How do I deploy a model on SAP AI Core?",
    "How does the orchestration service work in Generative AI Hub?",
    "What SAP products support Joule as a copilot?",
    "How do I store and query vector embeddings in SAP HANA Cloud?",
]
