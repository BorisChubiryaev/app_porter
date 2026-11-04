#!/usr/bin/env python3
"""Tells search engines that take IndexNow (Bing, Yandex and others) about the site's pages. Run it after a deploy that changes them.

Usage: python3 indexnow.py     (exit 1 unless the service accepts the list)
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import build


def main():
    config = json.loads((Path(__file__).resolve().parent / 'config.json').read_text('utf-8'))
    base, key = config['base_url'].rstrip('/'), config['indexnow_key']
    urls = [f'{base}/' if l == build.LANGS[0] else f'{base}/{l}/' for l in build.LANGS]
    body = {'host': urlparse(base).netloc, 'key': key, 'keyLocation': f'{base}/{key}.txt', 'urlList': urls}
    request = urllib.request.Request('https://api.indexnow.org/indexnow', json.dumps(body).encode(), {'Content-Type': 'application/json; charset=utf-8', 'User-Agent': 'slotless-site'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f'{len(urls)} pages sent: HTTP {response.status}')
            return 0
    except urllib.error.HTTPError as e:
        print(f'[RED] IndexNow refused the list: HTTP {e.code}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
