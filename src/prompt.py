"""
prompt.py — the SINGLE shared image-generation prompt used by BOTH art engines
(regen_photo.py / Nano Banana 2 and regen_gpt.py / gpt-image-2), so they stay
identical. Style preamble + per-game setting + per-scene context.

Goal: a faithful photographic RE-RENDER of the exact same scene — same motif,
every element in the exact same position, same camera angle — only the medium
changes from pixel-art to photograph. The output is far higher-resolution than
the source, so the model must *resolve* the coarse pixels into real detail
rather than recolour them: invent the fine detail the original could not hold,
but never invent new elements.

Per-game strings live in build/context.json:
    "_setting" : one sentence describing the game's world (optional)
    "0".."N"   : one phrase per picture number
"""
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_CTX_PATH = os.path.join(_HERE, '..', 'build', 'context.json')
CONTEXT = json.load(open(_CTX_PATH)) if os.path.exists(_CTX_PATH) else {}

# Per-game world description. Kept OUT of the style block so one prompt serves
# several games: a wrong global setting fights the per-scene context (e.g.
# "medieval-fantasy" would try to medievalise The Pawn's piano and laboratory).
SETTING = CONTEXT.get('_setting', '')

STYLE = (
    'This is a low-resolution, 16-colour pixel-art picture from a 1980s Amiga adventure game — '
    'blocky, dithered and heavily pixelated. Render the EXACT SAME scene as a full, naturalistic, '
    'photorealistic photograph shot on location with a modern professional camera. It must be the '
    'exact same motif with every element in the exact same position: identical composition, '
    'framing, camera angle, perspective, scale and layout. Do NOT move, resize, rearrange or '
    'remove anything, do NOT introduce objects, figures or scenery that are not in the source, and '
    'do NOT change the viewpoint. Match the source down to the finest detail — even the individual '
    'waves and ripples on water, the reflections, and the exact shape and position of every small '
    'feature must stay the same. '

    'Change ONLY the medium — treat the pixel-art as an exact blueprint of what is where. This '
    'photograph is at a far higher resolution than the source, so much more detail is visible than '
    'the original pixels could ever hold, and you MUST fill in that missing detail faithfully: '
    'where a few flat pixels stand in for a face, a hand, a leaf, brickwork, a distant tree or a '
    'ripple, render the real thing in full, believable detail. Jagged, stair-stepped pixel edges '
    'are only a coarse approximation — resolve them into the smooth curves, straight lines and true '
    'silhouettes they were approximating. Never merely recolour, blur or smooth the original '
    'pixels: rebuild every thing as the real object it depicts, with realistic materials and fine '
    'micro-texture (weathered stone, aged wood, brass, iron, glass, cloth, water, foliage, skin), '
    'true depth and natural, believable lighting. '

    'The result MUST contain no visible pixels, no stair-stepped edges, no dithering, no '
    'posterisation and no flat blocky areas — a real photograph, not pixel art and not an '
    'illustration. Faithful to the original’s mood. No caption text or borders.')


def prompt_for(name):
    """Full prompt for an image file (e.g. 'pic_05.png'): STYLE + setting + scene context."""
    m = re.search(r'(\d+)', name)
    ctx = CONTEXT.get(str(int(m.group(1)))) if m else None
    p = STYLE
    if SETTING:
        p += ' Setting: %s' % SETTING
    if ctx:
        p += ' The scene is %s.' % ctx
    return p
