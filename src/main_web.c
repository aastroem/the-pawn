/*
 * main_web.c — Emscripten driver for the Magnetic Scrolls interpreter (emu.c),
 * replacing the ANSI/stdio front-end (main.c) with JS callbacks so the real
 * engine runs in the browser. Text -> terminal, status line -> status bar,
 * ms_showpic(n) -> JS renderer (which picks original vs. photoreal per toggle),
 * and line input via ASYNCIFY (the game awaits a typed command, yielding to the
 * browser in between).
 *
 * Build (see build_wasm.sh):
 *   emcc -O2 -sASYNCIFY --embed-file guild.mag --embed-file guild.gfx \
 *        main_web.c emu.c -o magnetic.js  (MODULARIZE, EXPORT_NAME=createMagnetic)
 *
 * The C interpreter is GPLv2 (Niclas Karlsson / David Kinder). Personal/research use.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <emscripten.h>
#include "defs.h"

type8 ms_gfx_enabled;

/* ---- imported JS callbacks (defined on the Module object) --------------- */
EM_JS(void, web_put,    (int c),          { Module.onChar(c); });
EM_JS(void, web_status, (int c),          { Module.onStatus(c); });
EM_JS(void, web_pic,    (int n, int mode),{ Module.onPic(n, mode); });

/* Await a command line from JS (needs ASYNCIFY). Returns a malloc'd C string. */
EM_ASYNC_JS(char*, web_getline, (void), {
  const s = await Module.getLine();
  const len = lengthBytesUTF8(s) + 1;
  const p = _malloc(len);
  stringToUTF8(s, p, len);
  return p;
});

/* ---- ms_* platform callbacks the engine calls -------------------------- */
type8 ms_load_file(type8s *name, type8 *ptr, type16 size) {
  FILE *f = fopen((const char *)name, "rb");
  if (!f) return 1;
  size_t r = fread(ptr, 1, size, f);
  fclose(f);
  return r != size;
}
type8 ms_save_file(type8s *name, type8 *ptr, type16 size) {
  FILE *f = fopen((const char *)name, "wb");
  if (!f) return 1;
  fwrite(ptr, 1, size, f);
  fclose(f);
  return 0;
}
void ms_statuschar(type8 c) { web_status(c); }
void ms_flush(void) {}
void ms_putchar(type8 c) { web_put(c); }

type8 ms_getchar(type8 trans) {
  static type8 buf[512];
  static int pos = 0, len = 0;
  if (pos >= len) {
    char *s = web_getline();            /* async: awaits a line from the page */
    int i = 0;
    while (s && s[i] && i < 510) { buf[i] = (type8)s[i]; i++; }
    buf[i++] = '\n';
    len = i; pos = 0;
    if (s) free(s);
  }
  return buf[pos++];
}

void ms_showpic(type32 c, type8 mode) { web_pic((int)c, (int)mode); }

void ms_fatal(type8s *txt) {
  const char *p = (const char *)txt;
  web_put('\n');
  while (p && *p) web_put((unsigned char)*p++);
  web_put('\n');
}
type8 ms_showhints(struct ms_hint *hints) { return 0; }
void ms_playmusic(type8 *midi_data, type32 length, type16 tempo) {}

/* ---- entry point ------------------------------------------------------- */
int main(void) {
  if (!(ms_gfx_enabled = ms_init((type8s *)"pawn.mag", (type8s *)"pawn.gfx", 0, 0))) {
    const char *e = "Couldn't start the game data.\n";
    while (*e) web_put((unsigned char)*e++);
    return 1;
  }
  ms_gfx_enabled--;                      /* 0 = no gfx, else enabled */
  type8 running = 1;
  while (running) running = ms_rungame();
  {
    const char *e = "\n[The game has ended.]\n";
    while (*e) web_put((unsigned char)*e++);
  }
  return 0;
}
