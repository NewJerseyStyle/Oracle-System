import os
from dotenv import load_dotenv

load_dotenv()

# RapidAPI Game Theory API
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
GAME_THEORY_API_URL = "https://game-theory-nash-equilibrium-predictor.p.rapidapi.com"
GAME_THEORY_HOST = "game-theory-nash-equilibrium-predictor.p.rapidapi.com"

# OpenRouter for LLM-powered extraction
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

# Local Deep Research Docker
LOCAL_RESEARCH_URL = os.getenv("LOCAL_RESEARCH_URL", "http://localhost:5000")
LDR_USERNAME = os.getenv("LDR_USERNAME", "researcher")
LDR_PASSWORD = os.getenv("LDR_PASSWORD", "researcher123")

# Analysis settings
DEFAULT_SALIENCE = 50
DEFAULT_CLOUT = 1.0
DEFAULT_RESOLVE = 50

def get_game_theory_headers():
    return {
        "Content-Type": "application/json",
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": GAME_THEORY_HOST
    }

def get_openrouter_headers():
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:7860",
        "X-Title": "Stakeholder Analysis Demo"
    }

def validate_config(require_openrouter: bool = False):
    """
    Validate configuration.
    
    Args:
        require_openrouter: If True, require OPENROUTER_API_KEY. 
                           If False (default), LDR's Ollama will be used as fallback.
    """
    errors = []
    if not RAPIDAPI_KEY:
        errors.append("RAPIDAPI_KEY not set")
    if require_openrouter and not OPENROUTER_API_KEY:
        errors.append("OPENROUTER_API_KEY not set")
    return errors
