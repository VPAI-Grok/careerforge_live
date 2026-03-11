"""
Configuration and environment setup for CareerForge.
This module MUST be imported before any google.adk or google.genai imports
to ensure the correct API keys are loaded and conflict resolution is applied
before the SDK initializes.
"""
import os
import pathlib
from dotenv import load_dotenv

# 1. Load the .env file
_env_path = pathlib.Path(__file__).parent / ".env"
load_dotenv(_env_path)

# 2. CRITICAL FIX for 1008 Error on Native Audio Model:
# The google-genai SDK prioritizes GEMINI_API_KEY over GOOGLE_API_KEY.
# If both are in .env, it uses the wrong one and fails with 1008 on
# gemini-2.5-flash-native-audio-preview-12-2025. Force it to use GOOGLE_API_KEY.
if "GOOGLE_API_KEY" in os.environ and "GEMINI_API_KEY" in os.environ:
    del os.environ["GEMINI_API_KEY"]
