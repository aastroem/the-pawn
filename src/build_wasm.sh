#!/bin/sh
# Build the Guild of Thieves WASM engine from the Magnetic interpreter (emu.c).
# Requires: emscripten (brew install emscripten), and guild.mag/guild.gfx + emu.c/defs.h
# staged next to main_web.c (emu.c/defs.h come from DavidKinder/Magnetic Generic/).
set -e
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:$PATH"
FLAGS="-O2 -sASYNCIFY -sMODULARIZE=1 -sEXPORT_NAME=createMagnetic \
  -sEXPORTED_FUNCTIONS=[_main,_malloc,_free] \
  -sEXPORTED_RUNTIME_METHODS=[lengthBytesUTF8,stringToUTF8,UTF8ToString] \
  -sALLOW_MEMORY_GROWTH=1 --embed-file guild.mag --embed-file guild.gfx"
emcc $FLAGS               main_web.c emu.c -o ../build/magnetic.js
emcc $FLAGS -sSINGLE_FILE=1 main_web.c emu.c -o ../build/magnetic_single.js
echo "built build/magnetic.js (+wasm) and build/magnetic_single.js"
