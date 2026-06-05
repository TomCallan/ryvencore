from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from ryvencore.web_backend import example_node_schemas, run_project


WEB_DIR = Path(__file__).resolve().parent
MAX_BODY_SIZE = 1_000_000


class WebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _send_json(self, status: int, payload: Dict[str, Any]):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/node-types':
            self._send_json(HTTPStatus.OK, {'node_types': example_node_schemas()})
            return

        if self.path == '/':
            self.path = '/index.html'

        super().do_GET()

    def do_POST(self):
        if self.path != '/api/run':
            self._send_json(HTTPStatus.NOT_FOUND, {'error': 'Not found'})
            return

        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 0 or length > MAX_BODY_SIZE:
                self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {'error': 'Request body too large'})
                return
            body = self.rfile.read(length)
            payload = json.loads(body.decode('utf-8') if body else '{}')
        except (ValueError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {'error': 'Invalid JSON body'})
            return

        project = payload.get('project')
        if not isinstance(project, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {'error': '"project" must be a JSON object'})
            return

        flow_index = payload.get('flowIndex', 0)
        if not isinstance(flow_index, int):
            flow_index = 0

        try:
            result = run_project(project, flow_index=flow_index)
            self._send_json(HTTPStatus.OK, result)
        except Exception as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {'error': str(exc)})


def main():
    parser = argparse.ArgumentParser(description='Run the ryvencore web frontend + Python backend')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind')
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), WebHandler)
    print(f'Serving ryvencore web app on http://{args.host}:{args.port}/')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
