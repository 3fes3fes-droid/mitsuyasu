from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import os
root=Path(__file__).resolve().parents[1];os.chdir(root)
print('http://127.0.0.1:8000/index.html')
ThreadingHTTPServer(('127.0.0.1',8000),SimpleHTTPRequestHandler).serve_forever()
