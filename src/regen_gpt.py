#!/usr/bin/env python3
"""
regen_gpt.py — regenerate The Guild of Thieves scenes photorealistically with
OpenAI **gpt-image-2** (images/edits, image-to-image), into art/regen_gpt/.

Uses per-scene context from build/context.json (authentic room names from the
game). Requests small WebP output from the API (output_format=webp +
output_compression) so downloads are light; saved locally as PNG for the
pipeline (the packer re-encodes to JPEG for the shipped page).

  OPENAI_API_KEY=... python3 tools/regen_gpt.py [--only pic_05.png] [--force]
                                                 [--quality high|medium|low]
"""
import argparse, base64, io, json, os, re, sys, requests
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.abspath(os.path.join(HERE, '..'))
ORIG = os.path.join(WEB, 'art', 'orig')
OUT = os.path.join(WEB, 'art', 'regen_gpt')
ENDPOINT = 'https://api.openai.com/v1/images/edits'
GEN_ENDPOINT = 'https://api.openai.com/v1/images/generations'
MODEL = 'gpt-image-2'

# Single shared prompt for BOTH engines — see tools/prompt.py
from prompt import STYLE, prompt_for  # noqa: E402,F401


def _b64(d):
    return base64.b64decode(d['data'][0]['b64_json']) if d.get('data') else None


def render(key, f, quality):
    """image-to-image; on a moderation refusal of the reference image, fall back
    to a text-only generation (composition fidelity suffers, but we get a scene)."""
    with open(os.path.join(ORIG, f), 'rb') as fh:
        r = requests.post(ENDPOINT, headers={'Authorization': 'Bearer ' + key},
            data={'model': MODEL, 'prompt': prompt_for(f), 'size': '1536x1024',
                  'quality': quality, 'output_format': 'webp', 'output_compression': 80},
            files={'image': (f, fh, 'image/png')}, timeout=300)
    d = r.json()
    raw = _b64(d)
    if raw:
        return raw
    err = str(d.get('error', {}).get('message', d.get('error')))[:160]
    print('[blocked: %s -> text-only]' % err[:60], end=' ', flush=True)
    r = requests.post(GEN_ENDPOINT,
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'},
        json={'model': MODEL, 'prompt': prompt_for(f), 'size': '1536x1024',
              'quality': quality, 'output_format': 'webp', 'output_compression': 80},
        timeout=300)
    raw = _b64(r.json())
    if not raw:
        raise RuntimeError(err)
    return raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only'); ap.add_argument('--force', action='store_true')
    ap.add_argument('--quality', default='high', choices=['high', 'medium', 'low'])
    args = ap.parse_args()
    key = os.environ.get('OPENAI_API_KEY') or sys.exit('OPENAI_API_KEY not set')
    os.makedirs(OUT, exist_ok=True)

    files = sorted(f for f in os.listdir(ORIG) if f.endswith('.png'))
    if args.only:
        files = [f for f in files if f == args.only]
    done = 0
    for f in files:
        out = os.path.join(OUT, f)
        if os.path.exists(out) and not args.force:
            print('skip', f); done += 1; continue
        print('gpt-regen', f, '...', end=' ', flush=True)
        try:
            raw = render(key, f, args.quality)
            im = Image.open(io.BytesIO(raw)).convert('RGB')
            # gpt-image-2 only outputs 3:2 (1536x1024). Keep the WHOLE frame
            # (no cropping) and SQUEEZE it to the original picture's wide
            # aspect — squish the height so it fills the same box as the
            # other art sets and lines up on toggle.
            ow, oh = Image.open(os.path.join(ORIG, f)).size
            w, h = im.size
            im = im.resize((w, round(w * oh / ow)), Image.LANCZOS)   # squeeze to orig aspect
            im.save(out)
            print('ok', round(len(raw) / 1024), 'KB dl,', '%dx%d' % im.size); done += 1
        except Exception as e:                       # noqa: BLE001
            print('EXC', repr(e)[:150])
    print('\n%d/%d -> art/regen_gpt/' % (done, len(files)))


if __name__ == '__main__':
    main()
