"""
Mind-Guard Asia — Python Flask Backend
Serves the HTML frontend and proxies chat requests to OpenAI (gpt-4o-mini).

Usage:
  1. Add your key to .env: OPENAI_API_KEY=sk-...
  2. pip install -r requirements.txt
  3. python app.py
  4. Open http://localhost:5001
"""

import os
import json
from flask import Flask, request, Response, stream_with_context, send_from_directory
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


# ─── Static routes ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Serve the main Mind-Guard HTML app."""
    return send_from_directory(BASE_DIR, 'index.html')


# ─── API routes ──────────────────────────────────────────────────────────────

@app.route('/api/health')
def health():
    """Health check — confirms server and API key status."""
    key_ok = bool(os.getenv('OPENAI_API_KEY', '').startswith('sk-'))
    return {'status': 'ok', 'model': 'gpt-4o-mini', 'api_key_set': key_ok}


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Proxy chat requests to OpenAI with Server-Sent Events streaming.

    Request body (JSON):
        { "messages": [ {"role": "system"|"user"|"assistant", "content": "..."}, ... ] }

    Response:
        text/event-stream
        data: {"content": "<chunk>"}\n\n
        ...
        data: [DONE]\n\n
    """
    data = request.get_json(force=True, silent=True) or {}
    messages = data.get('messages', [])

    if not messages:
        return {'error': 'No messages provided'}, 400

    if not os.getenv('OPENAI_API_KEY'):
        return {'error': 'OPENAI_API_KEY not set in .env'}, 500

    def generate():
        try:
            stream = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=messages,
                stream=True,
                max_tokens=600,
                temperature=0.85,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    payload = json.dumps({'content': delta.content})
                    yield f'data: {payload}\n\n'

        except Exception as e:
            error_payload = json.dumps({'error': str(e)})
            yield f'data: {error_payload}\n\n'

        finally:
            yield 'data: [DONE]\n\n'

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',   # disable nginx buffering if behind proxy
            'Connection': 'keep-alive',
        },
    )


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import socket
    port = int(os.getenv('PORT', 5001))
    key_set = os.getenv('OPENAI_API_KEY', '').startswith('sk-')

    # Get local network IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = '127.0.0.1'

    print()
    print('  🧠  Mind-Guard Asia')
    print(f'  🖥️   Local    : http://localhost:{port}')
    print(f'  📱  Network  : http://{local_ip}:{port}  ← akses dari HP/device lain')
    print(f'  🤖  Model    : gpt-4o-mini')
    print(f'  🔑  API Key  : {"✅  loaded from .env" if key_set else "⚠️   NOT SET — edit .env first"}')
    print()

    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)
