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
    'photograph. '

    # The user asked for this explicitly: name the input's poverty, and make the
    # operation super-resolution — the palette and the pixel grid are limits to be
    # undone, not features to be reproduced.
    'The blueprint is very low resolution, only a few hundred pixels across, and it is limited to '
    'a palette of just 16 colours. Super-scale it. Everything it renders coarsely — a shape a few '
    'pixels wide, a colour it could only approximate, a shade it had to fake — is a limit of that '
    '1980s hardware, and it stands for the full, continuous, high-resolution reality behind it. '
    'Restore that reality: millions of colours, smooth gradients, and detail resolved all the way '
    'down to what a modern full-frame sensor records. '

    'Above all else the two must register: they are shown in a viewer that switches '
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
    'whole and believable. '

    # "Complete what is hinted at, add nothing new" — both halves positive, and the
    # completion licenses DETAIL on shapes already present, never new objects.
    # Naming "an object half lost in shadow" put a door and wall lamps into a dark
    # wall; empty space must be stated as staying empty.
    'Every shape the blueprint already shows gains the detail it always had: a face reduced to a '
    'smudge of pixels resolves into one particular face, a few green pixels into individual leaves, '
    'a flat band of wall into its courses and mortar, a suggested texture into the real grain of '
    'the thing. The photograph holds the very same things as the blueprint, seen properly for the '
    'first time — its inventory of objects is already complete, and each object simply becomes '
    'itself in full. Where the blueprint is bare, dark or empty, the photograph is bare, dark and '
    'empty too, with nothing in it but real air, real light and the surfaces already there. '

    'Creatures, figures and impossible places are as physically present, as '
    'ordinarily lit and as plainly real as everything else in the frame. ')

# [style] — positive photographic description; the camera Kenneth specified
STYLE_TAIL = (
    'The result is a straight, unretouched photograph shot on a Sony Alpha 7R VI with an '
    'appropriate fixed lens using the right aperture for the shot: natural available light, '
    'physically correct shadows and reflections, natural depth of field, true-to-life colour, '
    'continuous photographic tone and crisp optical detail throughout, at the same time of day, '
    'weather and quality of light as the blueprint. A clean, full-bleed frame.')

# Kept for backwards compatibility with anything importing STYLE.
STYLE = OPEN + SCENARIO + STYLE_TAIL

# Second pass. Its input is pass 1's own output, which already registers with the
# blueprint, so composition is cheap to hold and every word can buy realism.
# A raw reference in pass 1 keeps the geometry but also keeps the source's flat,
# illustrated look; this pass converts that look into photography.
_REFINE_HEAD = (
    'Re-photograph this image as a real photograph, keeping every element in precisely the same '
    'place: identical composition, framing, camera angle, perspective and scale, with every object '
    'the same size and in the same position. Change only how it is rendered. ')

_REFINE_BODY = (
    'It becomes an actual photograph taken on a Sony Alpha 7R VI with an appropriate fixed lens at '
    'the right aperture: real optics with natural depth of field and a soft falloff to the '
    'background, fine sensor-level detail, believable micro-contrast, subtle lens vignetting, '
    'natural available light with physically correct shadows, bounce and reflection, and '
    'true-to-life colour. '

    # The raw reference in pass 1 copies the source's dither grid into cloth and stone, where it
    # reads as weave. Say what a real surface looks like — irregular — rather than naming the flaw.
    'Every surface carries the irregular, one-of-a-kind texture of the real material it is made '
    'of, varying everywhere across the frame: the wandering grain and knots of wood, the random '
    'grit and erosion of stone, the drawn marks and dents of metal, the loose fibres and folds of '
    'cloth, the veins of a leaf, the pores and fine hairs of skin — each unique, each catching that '
    'light differently. Anything the lens would resolve as living matter is soft, warm and alive. '
    'The finished frame is indistinguishable from a photograph taken on location. A clean, '
    'full-bleed frame.')

REFINE = _REFINE_HEAD + _REFINE_BODY


def refine_for(name):
    """Pass-2 prompt. Naming the scene lets the model reason about its materials."""
    m = re.search(r'(\d+)', name)
    ctx = CONTEXT.get(str(int(m.group(1)))) if m else None
    p = _REFINE_HEAD
    if ctx:
        p += 'It is a photograph of %s. ' % ctx
    return p + _REFINE_BODY


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
