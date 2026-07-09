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

# Nano Banana 2 (there is no "1.5"); Pro = gemini-3-pro-image, older = gemini-2.5-flash-image
MODEL = os.environ.get('GEMINI_IMAGE_MODEL', 'gemini-3.1-flash-image')
ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent'

# Single shared prompt for BOTH engines — see tools/prompt.py
from prompt import STYLE, REFINE, prompt_for, refine_for  # noqa: E402,F401


class Blocked(RuntimeError):
    """Safety refusal — retrying the same request is pointless."""


def dither_mask(im, thresh=6, gmax=14):
    """Pixels belonging to an ordered-dither lattice, rather than to real detail.

    Two tests, and both are needed. A median leaves step edges alone but disturbs
    a checkerboard, so |image - median| finds the lattice. That alone flags ~70%
    of these frames, including thin one-pixel highlights — the lattice and a
    scythe blade live in the same frequency band. So intersect it with a
    flatness test on the *median* image, where real edges survive and the dither
    does not: what is left is dither sitting in an otherwise featureless area.
    """
    import numpy as np
    from PIL import ImageFilter
    g = np.asarray(im.convert('L'), float)
    m = np.asarray(im.convert('L').filter(ImageFilter.MedianFilter(3)), float)
    dith = np.abs(g - m) > thresh
    gx, gy = np.gradient(m)
    flat = np.hypot(gx, gy) < gmax                 # nothing real to lose here
    mask = dith & flat
    grow = mask.copy()                             # cover the lattice's own borders...
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            grow |= np.roll(np.roll(mask, dy, 0), dx, 1)
    return grow & flat                             # ...but never spill into structure


def reference_png(path, dedither=True, scale=3):
    """The reference image handed to the model.

    The 16-colour originals fake intermediate shades with an ordered dither — a
    regular 1-2px lattice (verified at pixel level on The Pawn's pic_03 robe).
    Image-to-image copies that lattice verbatim, so it resurfaces as woven or
    knitted cloth in the "photograph". Prompting cannot fix what is in the pixels.

    A whole-frame median or blur removes the lattice but equally softens thin
    one-pixel structures — a scythe blade, a railing — and the model then
    re-invents what was erased: that is where the drift, the invented window and
    the extra fire came from. A 3px median also cannot touch a 2px-period lattice
    at all. So: a 3x3 box blur, applied ONLY where the lattice sits in flat areas.
    """
    import numpy as np
    from PIL import ImageFilter
    im = Image.open(path).convert('RGB')
    if dedither:
        smooth = np.asarray(im.filter(ImageFilter.BoxBlur(1)), float)
        mask = dither_mask(im)[..., None]
        im = Image.fromarray(np.where(mask, smooth, np.asarray(im, float)).astype('uint8'))
    im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return buf.getvalue()


def call(key, prompt, in_path, aspect='16:9', retries=3, include_image=True,
         dedither=True, ref_bytes=None):
    gen = {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': aspect}}
    parts = [{'text': prompt}]
    if include_image:
        ref = ref_bytes if ref_bytes is not None else reference_png(in_path, dedither)
        parts.append({'inline_data': {'mime_type': 'image/png',
                                      'data': base64.b64encode(ref).decode()}})
    body = json.dumps({'contents': [{'parts': parts}], 'generationConfig': gen}).encode()
    url = (ENDPOINT % MODEL) + '?key=' + key
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
    ap.add_argument('--outdir', help='write here instead of art/regen_hi (for A/B tests)')
    ap.add_argument('--no-dedither', dest='dedither', action='store_false',
                    help='send the raw pixel art as the reference (no median filter)')
    ap.add_argument('--refine', action='store_true',
                    help='second pass: re-photograph pass 1 output for realism')
    ap.add_argument('--hires', action='store_true',
                    help='save native full-resolution output to art/regen_hi/ '
                         '(does not touch the existing art/regen/ files)')
    args = ap.parse_args()
    key = os.environ.get('GEMINI_API_KEY') or sys.exit('GEMINI_API_KEY not set')

    outdir = args.outdir or (REGEN_HI if args.hires else REGEN)
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
            src = os.path.join(ORIG, f)
            try:
                png = call(key, prompt_for(f), src, dedither=args.dedither)
            except Blocked as b:
                # Smoothing can push a reference over a safety threshold that the
                # raw pixel-art never crossed, so try the raw image before giving
                # up the reference entirely: text-only loses the composition.
                print('[blocked: %s -> raw ref]' % b, end=' ', flush=True)
                try:
                    png = call(key, prompt_for(f), src, dedither=False)
                except Blocked as b2:
                    print('[blocked: %s -> text-only]' % b2, end=' ', flush=True)
                    png = call(key, prompt_for(f), None, include_image=False)
            if args.refine:
                print('[refine]', end=' ', flush=True)
                try:
                    png = call(key, refine_for(f), None, ref_bytes=png)
                except Exception as e:      # keep pass 1 rather than lose the frame
                    print('[refine failed: %s]' % str(e)[:40], end=' ', flush=True)
            save(png, out, size, aspect)
            got = Image.open(out).size
            print('ok', got); done += 1
        except Exception as e:
            print('FAILED:', str(e)[:120])
        time.sleep(1)
    print('\n%d/%d done -> %s' % (done, len(files), os.path.relpath(outdir, WEB)))


if __name__ == '__main__':
    main()
