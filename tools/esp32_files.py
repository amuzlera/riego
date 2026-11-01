#!/usr/bin/env python3
"""Authenticated recovery client; configuration/key never appear in argv."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='192.168.1.50')
    parser.add_argument('--config', type=Path, default=ROOT / 'esp32/recovery_config.json')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    sub.add_parser('health')
    sub.add_parser('reset')
    get = sub.add_parser('get')
    get.add_argument('remote')
    get.add_argument('output', type=Path)
    put = sub.add_parser('put')
    put.add_argument('local', type=Path)
    put.add_argument('remote')
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    route = {'list': '/files', 'health': '/health', 'reset': '/reset'}.get(args.command)
    method, data = 'GET', None
    headers = {'X-API-Key': cfg['api_key']}
    if args.command in ('get', 'put'):
        if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.' for c in args.remote):
            parser.error('Use a simple filename without directories')
        route = '/files/' + args.remote
    if args.command == 'put':
        method, data = 'PUT', args.local.read_bytes()
        headers['X-Content-SHA256'] = hashlib.sha256(data).hexdigest()
        headers['Content-Type'] = 'application/octet-stream'
    if args.command == 'reset':
        method, data = 'POST', b''
    req = urllib.request.Request('http://%s:%s%s' % (args.host, cfg.get('port', 81), route), data=data, headers=headers, method=method)
    # Local network: ignore HTTP_PROXY settings.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=15) as response:
        result = response.read()
        if args.command == 'get':
            if hashlib.sha256(result).hexdigest() != response.headers.get('X-Content-SHA256'):
                raise RuntimeError('Download checksum mismatch')
            args.output.write_bytes(result)
            args.output.chmod(0o600)
            print('Saved:', args.output)
        else:
            print(result.decode())


if __name__ == '__main__':
    main()
