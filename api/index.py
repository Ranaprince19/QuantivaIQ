import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from python.web_dashboard import app
except Exception:
    from flask import Flask
    app = Flask(__name__)
    error_trace = traceback.format_exc()

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return f"<h2>Import Error</h2><pre>{error_trace}</pre>", 500
