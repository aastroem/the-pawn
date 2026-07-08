#!/usr/bin/env python3
"""
regen_photo.py — regenerate The Guild of Thieves scenes as naturalistic,
period-accurate PHOTOREALISTIC images (Nano Banana 2 / Gemini image-to-image
over the original Magnetic Scrolls pictures).

Style: photoreal as if shot on location with a modern pro camera, but faithful
to each original scene's medieval-fantasy mood and composition (not stylized or
modernized). Reference image carries the composition; prompt sets the look.

Personal / research artifact. Uses $GEMINI_API_KEY. Resumable (skips existing).
  GEMINI_API_KEY=... python3 tools/regen_photo.py --only pic_05.png
  GEMINI_API_KEY=... python3 tools/regen_photo.py
"""
import argparse, base64, io, json, os, ssl, sys, time, urllib.request, urllib.error
from PIL import Image

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CTX = ssl.create_default_context()

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.abspath(os.path.join(HERE, '..'))
ORIG = os.path.join(WEB, 'art', 'orig')
REGEN = os.path.join(WEB, 'art', 'regen')
REGEN_HI = os.path.join(WEB, 'art', 'regen_hi')   # full-res output (separate)

MODEL = 'gemini-3.1-flash-image'   # Nano Banana 2
ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent' % MODEL

# Single shared prompt for BOTH engines — see tools/prompt.py
from prompt import STYLE, prompt_for  # noqa: E402,F401


class Blocked(RuntimeError):
    """Safety refusal — retrying the same request is pointless."""


def call(key, prompt, in_path, aspect='16:9', retries=3, include_image=True):
    gen = {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': aspect}}
    parts = [{'text': prompt}]
    if include_image:
        with open(in_path, 'rb') as f:
            parts.append({'inline_data': {'mime_type': 'image/png',
                                          'data': base64.b64encode(f.read()).decode()}})
    body = json.dumps({'contents': [{'parts': parts}], 'generationConfig': gen}).encode()
    url = ENDPOINT + '?key=' + key
    last = None
    for att in range(retries):
        try:
            req = urllib.request.Request(url, data=body,
                                         headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
                data = json.load(r)
            # a prompt/image-level refusal: never retry, let the caller fall back
            fb = data.get('promptFeedback') or {}
            if fb.get('blockReason'):
                raise Blocked(fb['blockReason'])
            for c in data.get('candidates', []):
                for p in c.get('content', {}).get('parts', []):
                    inl = p.get('inlineData') or p.get('inline_data')
                    if inl and inl.get('data'):
                        return base64.b64decode(inl['data'])
                if c.get('finishReason') in ('PROHIBITED_CONTENT', 'SAFETY',
                                             'IMAGE_SAFETY', 'IMAGE_OTHER'):
                    raise Blocked(c['finishReason'])
            last = 'no image: ' + json.dumps(data)[:200]
        except Blocked:
            raise
        except urllib.error.HTTPError as e:
            last = 'HTTP %s' % e.code
            if e.code in (429, 500, 503):
                time.sleep(2 * (att + 1)); continue
            break
        except Exception as e:
            last = repr(e); time.sleep(2 * (att + 1))
    raise RuntimeError(last)


def crop_to_aspect(im, tar):
    """center-crop im to aspect ratio tar (no distortion)."""
    w, h = im.size
    if w / h > tar:
        nw = round(h * tar); x = (w - nw) // 2; return im.crop((x, 0, x + nw, h))
    nh = round(w / tar); y = (h - nh) // 2; return im.crop((0, y, w, y + nh))


def save(png, out_path, size, aspect=None):
    """size=None -> keep native res. aspect set -> center-crop to that ratio so
    the photoreal frame matches the original picture (for toggle alignment)."""
    im = Image.open(io.BytesIO(png)).convert('RGB')
    if aspect:
        im = crop_to_aspect(im, aspect)
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    im.save(out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only'); ap.add_argument('--force', action='store_true')
    ap.add_argument('--hires', action='store_true',
                    help='save native full-resolution output to art/regen_hi/ '
                         '(does not touch the existing art/regen/ files)')
    args = ap.parse_args()
    key = os.environ.get('GEMINI_API_KEY') or sys.exit('GEMINI_API_KEY not set')

    outdir = REGEN_HI if args.hires else REGEN
    os.makedirs(outdir, exist_ok=True)

    files = sorted(f for f in os.listdir(ORIG) if f.endswith('.png'))
    if args.only:
        files = [f for f in files if f == args.only]
    done = 0
    for f in files:
        out = os.path.join(outdir, f)
        if os.path.exists(out) and not args.force:
            print('skip', f); done += 1; continue
        ow, oh = Image.open(os.path.join(ORIG, f)).size
        size = None if args.hires else (ow, oh)
        aspect = (ow / oh) if args.hires else None   # crop to the original's aspect
        print('photo-regen', f, ('(native res)' if args.hires else size), '...', end=' ', flush=True)
        try:
            try:
                png = call(key, prompt_for(f), os.path.join(ORIG, f))
            except Blocked as b:
                # Gemini sometimes refuses the *reference image* (e.g. a likeness).
                # Composition fidelity suffers, but the scene still gets made.
                print('[blocked: %s -> text-only]' % b, end=' ', flush=True)
                png = call(key, prompt_for(f), None, include_image=False)
            save(png, out, size, aspect)
            got = Image.open(out).size
            print('ok', got); done += 1
        except Exception as e:
            print('FAILED:', str(e)[:120])
        time.sleep(1)
    print('\n%d/%d done -> %s' % (done, len(files), os.path.relpath(outdir, WEB)))


if __name__ == '__main__':
    main()
