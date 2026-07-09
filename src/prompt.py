"""
prompt.py — the SINGLE shared image-generation prompt used by BOTH art engines
(regen_photo.py / Nano Banana 2 and regen_gpt.py / gpt-image-2), so they stay
identical.

Structured after Google's Nano Banana prompting guide:
  * open with a strong verb naming the primary operation;
  * narrative prose, not keyword lists;
  * multimodal form = [reference] + [relationship instruction] + [new scenario];
  * "be explicit about what to keep exactly the same";
  * POSITIVE FRAMING ONLY — "empty street", never "no cars".

That last rule is load-bearing. An earlier version of this prompt listed the
failure modes it wanted to avoid (weave, knitting, tapestry, painting,
sculpture...) and the model produced exactly those: naming them summons them.
Every constraint here is therefore phrased as a description of the target.

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
# several games, and free of parenthetical examples: a text-only fallback has no
# reference image, so any example in here gets drawn (a stray piano, a lab...).
SETTING = CONTEXT.get('_setting', '')

# [strong verb] + [relationship to the reference] + [what to keep identical].
# The registration sentence is the whole point of the project: the viewer toggles
# between the blueprint and this photograph, so anything that moves is a defect.
OPEN = (
    'Photograph this exact scene for real, on location. We are reconstructing low-resolution '
    '16-bit-era game graphics as real-life photographs: the attached picture is a 16-colour image '
    'from a 1980s Amiga adventure game, and it is the exact structural blueprint for the '
    'photograph. Above all else the two must register: they are shown in a viewer that switches '
    'back and forth between them, so every element has to sit in precisely the same place in both, '
    'and cross-fading one into the other must reveal no movement at all. Keep the composition, '
    'framing, camera angle, perspective, scale, and the position and silhouette of every single '
    'object exactly as they are, down to the shape and place of every small feature. Show exactly '
    'the objects, figures and scenery that the blueprint shows, seen from exactly its viewpoint. ')

# Only for scenes that actually contain water — naming water in a prompt for a dry
# scene summons it (it is why the forest of roots came back as a swamp).
WATER = ('The individual waves and ripples on the water, and the reflections in it, keep exactly '
         'the shape and position they have in the blueprint. ')

_WATER_RE = re.compile(
    r'\b(water|river|lake|sea|ocean|pond|pool|stream|brook|canal|moat|boat|jetty|'
    r'waterfall|fountain|marsh|swamp|wave|ripple)s?\b', re.I)

# [new scenario] — how to read the blueprint, phrased entirely as what to render
SCENARIO = (
    'Rebuild every thing in it as the real, physical subject it depicts, standing in front of the '
    'lens: real materials with fine micro-texture — weathered stone, aged wood, brass, iron, '
    'glass, foliage, skin — with real depth, real air and real light between them. Where '
    'the blueprint fakes a shade with a fine repeating pixel pattern, that stands for a smooth '
    'continuous gradient: render those areas as smooth continuous tone in the real material. '
    'Where its edges climb in coarse steps, that stands for a clean curve or a straight line: '
    'render the true silhouette it approximates. This photograph resolves far more than the '
    'blueprint could hold, so show the fine detail it had to leave out — where a handful of flat '
    'pixels stand in for a face, a hand, a leaf, brickwork or a distant tree, show that thing '
    'whole and believable. Fantastical subjects are realised as practical props, built sets, '
    'costumes, make-up and creature effects, and then photographed. ')

# [style] — positive photographic description; the camera Kenneth specified
STYLE_TAIL = (
    'The result is a straight, unretouched photograph shot on a Sony Alpha 7R VI with an '
    'appropriate fixed lens using the right aperture for the shot: natural available light, '
    'physically correct shadows and reflections, natural depth of field, true-to-life colour, '
    'continuous photographic tone and crisp optical detail throughout, faithful to the mood of the '
    'original. A clean, full-bleed frame.')

# Kept for backwards compatibility with anything importing STYLE.
STYLE = OPEN + SCENARIO + STYLE_TAIL

# Second pass. Its input is pass 1's own output, which already registers with the
# blueprint, so composition is cheap to hold and every word can buy realism.
# A raw reference in pass 1 keeps the geometry but also keeps the source's flat,
# illustrated look; this pass converts that look into photography.
REFINE = (
    'Re-photograph this image as a real photograph, keeping every element in precisely the same '
    'place: identical composition, framing, camera angle, perspective and scale, with every object '
    'the same size and in the same position. Change only how it is rendered. It becomes an actual '
    'photograph taken on a Sony Alpha 7R VI with an appropriate fixed lens at the right aperture: '
    'real optics with natural depth of field and a soft falloff to the background, fine sensor-level '
    'detail, believable micro-contrast, subtle lens vignetting, natural available light with '
    'physically correct shadows, bounce and reflection, and true-to-life colour. Surfaces gain the '
    'response of the real materials they are — the grain and pores of wood, stone, metal, cloth, '
    'leaf and skin under that light. The finished frame is indistinguishable from a photograph '
    'taken on location. A clean, full-bleed frame.')


def has_water(num, ctx):
    """True if this scene really contains water. Word-boundary match, so that
    'seated' does not count as 'sea'. `_water` lists scenes whose description
    omits the water that is plainly in the picture."""
    if str(num) in CONTEXT.get('_water', []):
        return True
    return bool(ctx and _WATER_RE.search(ctx))


def prompt_for(name):
    """Full prompt for an image file (e.g. 'pic_05.png').

    Order follows the guide's formula — subject/location before style.
    """
    m = re.search(r'(\d+)', name)
    num = int(m.group(1)) if m else None
    ctx = CONTEXT.get(str(num)) if m else None
    p = OPEN
    if has_water(num, ctx):
        p += WATER
    if ctx:
        p += 'The scene is %s. ' % ctx
    if SETTING:
        p += 'It sits in %s ' % SETTING
    return p + SCENARIO + STYLE_TAIL
