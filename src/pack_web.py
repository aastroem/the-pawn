#!/usr/bin/env python3
"""
pack_web.py — inline the WASM engine + all four art sets into ONE self-contained
pawn_packed.html that opens directly (no server, no external files).

  - the engine: build/magnetic_single.js (wasm embedded via emcc -sSINGLE_FILE)
  - the art: art/orig/*.png (blocky originals) + art/regen_hi/*.png (photoreal),
    embedded as data: URIs in window.PAWN_IMG keyed "set/file".
"""
import base64, io, json, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.abspath(os.path.join(HERE, '..'))
OUT = os.path.join(WEB, 'pawn_packed.html')


def png_uri(path):
    with open(path, 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode('ascii')


def photo_uri(path, quality=62, max_w=1024):
    # downscale to display size (the picture box never exceeds ~1076px) and
    # encode as WebP (~30% smaller than JPEG at equal quality; all current
    # browsers support it) -> much smaller page, no visible loss at display size.
    im = Image.open(path).convert('RGB')
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'WEBP', quality=quality, method=6)
    return 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def collect(setname):
    d = os.path.join(WEB, 'art', setname)
    imgs = {}
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if not f.endswith('.png'):
                continue
            path = os.path.join(d, f)
            # photoreal sets -> downscaled WebP; originals stay lossless PNG (tiny)
            imgs[setname + '/' + f] = photo_uri(path) if setname in ('regen_hi', 'regen_gpt') else png_uri(path)
    return imgs


def main():
    html = open(os.path.join(WEB, 'pawn.html'), encoding='utf-8').read()
    engine = open(os.path.join(WEB, 'build', 'magnetic_single.js'), encoding='utf-8').read()

    imgs = {}
    imgs.update(collect('orig'))
    imgs.update(collect('c64'))          # C64 originals (crisp PNG, tiny)
    imgs.update(collect('regen_hi'))
    imgs.update(collect('regen_gpt'))

    # inline the engine in place of the external <script src>
    html = html.replace('<script src="build/magnetic.js"></script>',
                        '<script>\n' + engine + '\n</script>')
    # inject the art map before the host script (which reads window.PAWN_IMG)
    blob = '<script>window.PAWN_IMG = ' + json.dumps(imgs, separators=(',', ':')) + ';</script>\n'
    marker = '<script src="build/magnetic.js">'
    # engine already replaced; inject the blob right before the (now inline) engine
    idx = html.find('<script>\n' + engine[:40])
    if idx == -1:
        # fallback: inject before the host IIFE
        idx = html.rfind('<script>')
    html = html[:idx] + blob + html[idx:]

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    n_o = sum(1 for k in imgs if k.startswith('orig/'))
    n_h = sum(1 for k in imgs if k.startswith('regen_hi/'))
    n_g = sum(1 for k in imgs if k.startswith('regen_gpt/'))
    print('wrote %s  (%.1f MB)  art: %d orig + %d nano + %d gpt'
          % (os.path.relpath(OUT, WEB), os.path.getsize(OUT) / 1e6, n_o, n_h, n_g))


if __name__ == '__main__':
    main()
