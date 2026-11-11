#!/usr/bin/env python3
"""Copy only the files the app needs into dist/ for deployment (Cloudflare Pages).

Cloudflare Pages settings:
  Build command:           python3 tools/build_dist.py
  Build output directory:  dist

Everything else in the repo (material/, tools/, STATUS.md, README.md, …) stays on GitHub
and is NOT published. Original-page scans (assets/page-*.jpg) are never copied, even if
they exist locally.
"""
import os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'dist')
FILES = ['index.html', 'app.js', 'style.css', 'sw.js', 'manifest.webmanifest',
         'data.js', 'dictionary.js', 'assets/icon-192.png', 'assets/icon-512.png']


def main():
    missing = [f for f in FILES if not os.path.exists(os.path.join(ROOT, f))]
    if missing:
        sys.exit('missing files: ' + ', '.join(missing))
    shutil.rmtree(DIST, ignore_errors=True)
    for f in FILES:
        dst = os.path.join(DIST, f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(ROOT, f), dst)
    total = sum(os.path.getsize(os.path.join(DIST, f)) for f in FILES)
    print(f'dist/: {len(FILES)} files, {total / 1024:.0f} KB')


if __name__ == '__main__':
    main()
