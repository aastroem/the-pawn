"""
prompt.py — the SINGLE shared image-generation prompt used by BOTH art engines
(regen_photo.py / Nano Banana 2 and regen_gpt.py / gpt-image-2), so they stay
identical.

Arrived at by ablation; every rule below cost at least one bad batch to learn.

  * POSITIVE FRAMING ONLY — "empty street", never "no cars". An early version
    listed what to avoid (knitting, weave, tapestry, painting, sculpture) and
    the model produced exactly those. Naming a failure mode summons it.
  * NEVER describe what the source LOOKS like. "pixel", "pattern", "coarse",
    "blocky", "dithered", "Amiga", "1980s" all stay out: they anchor the model
    to the artifacts. But naming what the source LACKS — resolution, colours —
    is different, and *removes* artifacts: with it, a mosaic floor renders as
    broad polished slabs; without it, as thousands of tiny chips.
  * Registration is the point of the project (the page toggles between the two
    images), so it is stated first and repeated in the refine pass.
  * The invention guard must be COUNTABLE. "The frame holds nothing besides"
    still produced three arched openings on a wall that has one; "exactly as
    many openings as the reference shows" is checkable by the model.
  * "Imagine freely" licenses invented *things*, not just invented detail. The
    detail an object gets must stop at that object's own outline.

Two passes (regen_photo.py --refine): pass 1 sees the RAW pixel art; pass 2 sees
only pass 1's output. Filtering the reference first weakens the model's grip on
the source, and the weakened grip is what lets composition drift.

Per-game strings live in build/context.json:
    "_setting" : one sentence describing the game's world (optional)
    "_water"   : scene numbers whose picture contains water (optional)
    "0".."N"   : one phrase per picture number
"""
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_CTX_PATH = os.path.join(_HERE, '..', 'build', 'context.json')
CONTEXT = json.load(open(_CTX_PATH)) if os.path.exists(_CTX_PATH) else {}

# Per-game world description. Free of people and of examples: a text-only
# fallback has no reference image, so anything named here gets drawn.
SETTING = CONTEXT.get('_setting', '')

# [what this is] + [what must not move]
OPEN = (
    'A real-life photograph taken on location, perfectly matching the composition and alignment of '
    'the attached layout. Reconstruct this exact scene with flawless, modern high-resolution '
    'clarity. Every shape, object and figure from the reference sits in precisely the same place, '
    'keeping identical framing, camera angle, perspective, scale and silhouettes, so cross-fading '
    'between the two reveals zero movement. Replicate the scene using millions of smooth, '
    'continuous colours and lifelike gradients. ')

# [what the source lacks, and the operation] — resolution and colour count only
SUPERSCALE = (
    'The attached reference is a very low-resolution image holding only a handful of colours. This '
    'is a super-scaling of it: restore the full photographic resolution and the whole continuous '
    'colour range of a modern camera, so that everything the reference could only approximate — a '
    'shape too small to describe, a colour it had to round off, a shade it could only suggest — '
    'appears as the real thing, at its true size and its true level of detail. ')

# [read each shape, render that thing, keep its outline]
IDENTIFY = (
    'Read every shape in the reference for what it is, then render that thing as a photograph of '
    'itself. A tree is a real tree, with bark, boughs and individual leaves. A rock is a real rock, '
    'with grain, lichen and chipped edges. A mountain in the distance is a photograph of a distant '
    'mountain, with ridges, snow and the haze of the air in between. Give each thing the detail '
    'that that thing itself really has, and let its detail stop at its own outline: the silhouette, '
    'the edges and the position of every object stay exactly where the reference puts them, and the '
    'scene around them keeps the same contents, the same light and the same emptiness as the '
    'reference. ')

# [materials] + [the countable invention guard]
SCENARIO = (
    'Every object and surface is a real, physical subject standing in front of the lens: true '
    'materials with fine micro-texture — weathered stone, aged wood, brass, iron, glass, foliage, '
    'skin. All surfaces carry smooth, continuous tone and clean, true curves. Show crisp, '
    'believable photographic detail throughout: individual leaves on the trees, distinct courses of '
    'brickwork and mortar, fully resolved human features. '

    'The reference\'s inventory is already complete. Every single thing in the finished photograph '
    'traces back to something the reference shows, and the frame holds exactly those things and no '
    'others. Count them and match: the openings, doors, arches, windows, alcoves, carvings, lamps '
    'and fixtures are exactly as many as the reference shows, in exactly the places it shows them. '
    'A wall bearing one opening bears one opening; a plain wall stays a plain wall. Where the '
    'reference is bare, dark or empty, the photograph is bare, dark and empty too, holding only '
    'natural air, light and ambient shadow. Figures and creatures are physically present and '
    'ordinarily lit. ')

# The camera. iPhone rather than a pro body: "professional photography" pulls the
# model toward fine-art softness and artistic bokeh; mobile photography means deep
# depth of field, computational sharpness, and no artistic licence.
CAMERA = (
    'The result is a sharp, unretouched photograph shot on an iPhone 15 Pro: high-clarity mobile '
    'photography, deep depth of field keeping the entire scene in focus, natural available light, '
    'physically correct shadows, true-to-life vibrant colour, and crisp edge detail throughout, at '
    'the same time of day, weather and quality of light as the reference. A clean, full-bleed frame.')

# Only for scenes that really contain water: naming water in a prompt for a dry
# scene summons it (it turned a forest of roots into a swamp).
WATER = ('The individual waves and ripples on the water, and the reflections in it, keep exactly '
         'the shape and position they have in the reference. ')

_WATER_RE = re.compile(
    r'\b(water|river|lake|sea|ocean|pond|pool|stream|brook|canal|moat|boat|jetty|'
    r'waterfall|fountain|marsh|swamp|wave|ripple)s?\b', re.I)

STYLE = OPEN + SUPERSCALE + IDENTIFY + SCENARIO + CAMERA   # for anything importing STYLE


def has_water(num, ctx):
    """Word-boundary match, so 'seated' does not count as 'sea'. `_water` lists
    scenes whose description omits the water plainly in the picture."""
    if str(num) in CONTEXT.get('_water', []):
        return True
    return bool(ctx and _WATER_RE.search(ctx))


def prompt_for(name):
    """Pass-1 prompt for an image file (e.g. 'pic_05.png')."""
    m = re.search(r'(\d+)', name)
    num = int(m.group(1)) if m else None
    ctx = CONTEXT.get(str(num)) if m else None
    p = OPEN + SUPERSCALE
    if has_water(num, ctx):
        p += WATER
    if ctx:
        p += 'The scene is %s. ' % ctx
    if SETTING:
        p += 'It sits in %s ' % SETTING
    return p + IDENTIFY + SCENARIO + CAMERA


# Pass 2. Its input is pass 1's own output, which already registers with the
# reference, so every word here can buy realism rather than composition.
_REFINE_HEAD = (
    'Re-photograph this image as a real photograph, keeping every element in precisely the same '
    'place: identical composition, framing, camera angle, perspective and scale, with every object '
    'the same size and in the same position. Change only how it is rendered. ')

_REFINE_TAIL = (
    'It is a sharp, unretouched photograph shot on an iPhone 15 Pro: high-clarity mobile '
    'photography, deep depth of field keeping the entire scene in focus, natural available light, '
    'physically correct shadows, true-to-life vibrant colour, and crisp edge detail throughout. '
    'Every surface carries the irregular, one-of-a-kind texture of the real material it is made '
    'of, varying everywhere across the frame: the wandering grain and knots of wood, the random '
    'grit and erosion of stone, the loose fibres and folds of cloth, the veins of a leaf, the pores '
    'and fine hairs of skin. The finished frame is indistinguishable from a photograph taken on '
    'location. A clean, full-bleed frame.')

REFINE = _REFINE_HEAD + _REFINE_TAIL


def refine_for(name):
    """Pass-2 prompt. Naming the scene lets the model reason about its materials."""
    m = re.search(r'(\d+)', name)
    ctx = CONTEXT.get(str(int(m.group(1)))) if m else None
    p = _REFINE_HEAD
    if ctx:
        p += 'It is a photograph of %s. ' % ctx
    return p + _REFINE_TAIL
