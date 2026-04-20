"""
conftest.py — pytest path setup for the monorepo.
Adds project root and agent/ to sys.path so all tests can import
backend, agent, and FUSE modules without package-install hacks.
"""
import sys
import os

# Set dummy API keys before any module imports so clients that initialise
# at import time (e.g. Groq in structs.py) don't raise at collection time.
# Actual API calls are always mocked in the test suite.
os.environ.setdefault("GROQ_API_KEY", "dummy-groq-key-for-tests")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-key-for-tests")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Project root (gives access to backend/, FUSE/, agent/ as top-level packages)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# agent/ itself (because network.py / prompts.py use bare `from structs import *`)
AGENT_DIR = os.path.join(PROJECT_ROOT, "agent")
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

# backend/ itself (so backend.services can resolve `from database.db import ...`)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
