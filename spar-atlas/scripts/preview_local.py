#!/usr/bin/env python3
"""Isolated atlas preview: synthetic roster, local sign-up form, no upstream writes."""
import argparse
import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'recDHGcAaidjSHFg3'
entries = []
geocoding_config = {"apiKey": ""}
mock_geocoder = False


class Preview(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send(self, body, kind='text/html; charset=utf-8'):
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy',
                         "connect-src 'self' https://api.geoapify.com; form-action 'self'; object-src 'none'; base-uri 'self'")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == '/':
            page = (ROOT / 'index.html').read_text()
            page = re.sub(r"var SHEET_CSV = '[^']*';", "var SHEET_CSV = '';", page)
            page = re.sub(r"var GH_REPO = '[^']*';", "var GH_REPO = '';", page)
            page = re.sub(r"base: 'https://docs.google.com/forms/[^']*'", "base: '/preview-signup'", page)
            page = page.replace("if(window.claude &&", "if(false && window.claude &&")
            page = page.replace('Hannah adds you to the map, usually within a day.',
                                'LOCAL PREVIEW: submit the local mock form, then reload the atlas. Nothing is published.')
            page = page.replace('<title>', '<title>LOCAL PREVIEW — ')
            self.send(page)
        elif url.path == '/geocoder.js':
            self.send((ROOT / 'geocoder.js').read_text(), 'text/javascript')
        elif url.path == '/geocoding-config.js':
            self.send('window.ATLAS_GEOCODING = ' + json.dumps(geocoding_config) + ';', 'text/javascript')
        elif url.path == '/mock-geocoder' and mock_geocoder:
            query = parse_qs(url.query).get('text', [''])[0].lower()
            results = []
            if 'lenoir' in query:
                results = [{'city': 'Lenoir', 'state': 'North Carolina', 'country': 'United States of America',
                            'lat': 35.91402, 'lon': -81.53898, 'result_type': 'city', 'rank': {'confidence': 1}}]
            self.send(json.dumps({'results': results}), 'application/json')
        elif url.path == '/data/people.json':
            self.send(json.dumps({'entries': entries}), 'application/json')
        elif url.path == '/preview-signup':
            fields = parse_qs(url.query)
            hidden = ''.join('<input type="hidden" name="{}" value="{}">'.format(
                html.escape(k, quote=True), html.escape(v[0], quote=True)) for k, v in fields.items())
            self.send('<h1>Local sign-up simulation</h1><p>This stores your entry only in this preview server’s memory. '
                      'No Google Form, spreadsheet or database is contacted.</p><form method="post">' + hidden +
                      '<button>Submit locally</button></form>')
        else:
            self.send_error(404)

    def do_POST(self):
        if urlparse(self.path).path != '/preview-signup':
            self.send_error(404)
            return
        fields = parse_qs(self.rfile.read(int(self.headers.get('Content-Length', 0))).decode())
        get = lambda key: fields.get(key, [''])[0]
        projects = json.loads((ROOT / 'data/spar-f26-atlas.json').read_text())['projects']
        project = next((p for p in projects if p['title'] == get('entry.1196920667')), None)
        if not project or not get('entry.1431031113').strip():
            self.send_error(400, 'A known project and name are required')
            return
        entry = {'projectId': project['id'], 'name': get('entry.1431031113'),
                 'location': get('entry.1018615458'), 'linkedin': get('entry.1808384973')}
        old = next((e for e in entries if e['projectId'] == entry['projectId'] and
                    e['name'].lower() == entry['name'].lower()), None)
        if old is not None:
            old.update({k: v for k, v in entry.items() if v})
        else:
            entries.append(entry)
        self.send('<h1>Saved locally</h1><p>Return to the atlas, reload it, and select Globe.</p>'
                  '<a href="/">Open local atlas</a>')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--seed', action='store_true', help='Start with a synthetic Lenoir signup')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--geoapify-key-file', type=Path, help='Read a live test key from a local file')
    group.add_argument('--mock-geocoder', action='store_true', help='Use an isolated Geoapify-shaped Lenoir response')
    args = parser.parse_args()
    if args.geoapify_key_file:
        geocoding_config['apiKey'] = args.geoapify_key_file.read_text().strip()
    if args.mock_geocoder:
        mock_geocoder = True
        geocoding_config = {'apiKey': 'local-mock', 'endpoint': '/mock-geocoder', 'storage': None}
    if args.seed:
        entries.append({'projectId': PROJECT, 'name': 'Test Participant', 'location': 'lenoir, nc'})
    print(f'Isolated preview: http://127.0.0.1:{args.port} (Ctrl-C to stop)', flush=True)
    HTTPServer(('127.0.0.1', args.port), Preview).serve_forever()
