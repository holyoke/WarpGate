"""Verify health, real administrator authentication, and persisted branding."""
import json
import os
import urllib.request

base = os.environ.get('SMOKE_BASE_URL', 'http://127.0.0.1:8080')


def request(path, data=None, token=None, method=None):
    headers = {'Content-Type': 'application/json', 'X-Admin-UI-Request': 'true'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(base + path, body, headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as result:
        return json.load(result)


assert request('/health')['status'] == 'ok'
session = request('/api/v1/auth/login', {
    'email': os.environ['ADMIN_EMAIL'],
    'password': os.environ['ADMIN_PASSWORD'],
})['data']
token = session['access_token']
assert request('/api/v1/auth/me', token=token)['data']['role'] == 'admin'
assert request('/api/v1/settings/public')['data']['site_name'] == 'WarpGate'
print('Health, administrator login and WarpGate branding verified.')
