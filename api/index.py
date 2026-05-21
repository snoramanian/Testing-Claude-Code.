"""Vercel serverless entrypoint.

Re-exports the Flask WSGI `app` from the project root so Vercel's
@vercel/python runtime can serve it as a serverless function. Keeping
the actual Flask code in /app.py means `python app.py` still works
for local development.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app  # noqa: E402,F401
