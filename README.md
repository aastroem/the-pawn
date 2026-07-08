# The Pawn — web rebuild with four art sets

Play the classic 1985/86 Magnetic Scrolls text adventure **The Pawn** in your browser,
with a live toggle between **four** versions of every scene: the original **Amiga** and
**Commodore 64** artwork, and two AI **photoreal reshoots** (Nano Banana 2 and gpt-image-2).

▶ **Play:** https://aastroem.github.io/the-pawn/

- Type commands the usual way — `look`, `north`, `examine me`, `open door`, `take everything`…
- Press **G** (or the header buttons) to cycle **AMIGA → C64 → NANO BANANA → GPT-IMAGE 2**.
  The two pixel-art originals render crisp/blocky; the photoreal sets are matched to each
  scene's aspect so everything lines up on the toggle (with a subtle crossfade).
- Scenes crossfade as you walk between rooms. Most rooms have no picture of their own, so the
  engine leaves the last one up — it's **greyed out** while you're somewhere else.
- Drag the handle below the picture to resize it (aspect-locked). Works on mobile.

Personal / fan / research project — not affiliated with or endorsed by the rights holders.

## How it works

The real Magnetic Scrolls virtual machine runs in the browser: the interpreter's C core
(`emu.c`) is compiled to WebAssembly with Emscripten, driven by a small web front-end that
turns its text/graphics/input into an HTML terminal, a canvas and a keyboard. The engine
emits a *picture number* per scene; the page renders whichever art set is selected.
Everything is inlined into a single self-contained `index.html`.

## Credits

- **Original game — _The Pawn_ (1985/86).** Created by **Magnetic Scrolls** (written by
  Rob Steggles; company founded by Anita Sinclair, Ken Gordon and Hugh Steers), published by
  **Rainbird / Firebird**. Rights remain with the current holders (Strand Games and the
  original authors' heirs).
- **Original artwork.** By the Magnetic Scrolls artists — shown in the AMIGA and C64 modes,
  decoded from the games' own graphics data.
- **Interpreter — _Magnetic_.** By **Niclas Karlsson**, **David Kinder**, **Stefan Meier** and
  **Paul David Doherty** (https://github.com/DavidKinder/Magnetic, GNU GPL v2). Its `emu.c`
  core is compiled to WASM here.
- **Preserved Amiga data + C64 extraction.** Amiga `.mag`/`.gfx` from the **Magnetic Scrolls
  Memorial** (Stefan Meier, https://msmemorial.if-legends.org/); the C64 pictures were
  extracted from the original C64 disk images with **dMagnetic** (dettus, https://www.dettus.net/dMagnetic/).
- **Photorealistic scene regeneration.** Image-to-image with **Google Gemini "Nano Banana 2"**
  (`gemini-3.1-flash-image`) and **OpenAI `gpt-image-2`**, from the original pictures, prompted
  for a faithful photographic re-render of the exact same scene. Derivative works of the originals.
- **WebAssembly toolchain.** [Emscripten](https://emscripten.org/).
- **Web rebuild, WASM front-end and art pipeline.** Kenneth Aastrøm. The porting, build,
  extraction and art-regeneration tooling was created with the help of **Claude Opus 4.8** (Anthropic).

## Licensing

- The **interpreter** (`emu.c`, `defs.h`) and this project's engine glue (`src/main_web.c`) are
  under the **GNU General Public License v2** — see [`LICENSE`](LICENSE); corresponding source is
  in [`src/`](src/) (rebuild the WASM with `src/build_wasm.sh`, needs Emscripten + the game data).
- The **game, its text, and the original artwork** are © their respective rights holders and are
  included here for personal/fan use only. Rights holders: open an issue for takedown.

## Source layout

```
index.html         the game — self-contained (WASM engine + all four art sets inlined)
src/
  emu.c, defs.h     Magnetic interpreter core (GPLv2, DavidKinder/Magnetic)
  main_web.c        Emscripten driver: ms_* callbacks -> JS (text/gfx/input)
  build_wasm.sh     emcc build for the WASM engine
  prompt.py         the single shared image-generation prompt (both AI engines)
  regen_photo.py    Nano Banana 2 regeneration ; regen_gpt.py  gpt-image-2 regeneration
  pack_web.py       inline engine + art -> index.html
  context.json      per-scene descriptions (authentic room names from the game)
```
