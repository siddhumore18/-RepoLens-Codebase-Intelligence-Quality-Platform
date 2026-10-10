"""
RepoLens Unified Server Launcher
Starts the AI_Model Python microservice on port 5000.
"""

import sys
import os
import uvicorn

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from AI_Model.server import app

if __name__ == "__main__":
    print("=" * 70)
    print("   REPOLENS: LAUNCHING 3-TIER AI & ML CODEBASE INTELLIGENCE")
    print("=" * 70)
    print("AI Model Service:  http://127.0.0.1:5000")
    print("Swagger API Docs:  http://127.0.0.1:5000/docs")
    print("=" * 70)
    uvicorn.run(app, host="127.0.0.1", port=5000)
