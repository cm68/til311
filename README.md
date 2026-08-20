# TIL311 clone

A boardlet that replaces the Texas Instruments TIL311 hexadecimal display,
which is getting scarce.

## Goals

- **A functional drop-in for the TIL311 interface** — 4 data lines (A–D), a
  latch strobe, and a blanking input, on 5 V TTL — so it plugs in where a
  TIL311 was, same signals, same levels.
- **A faithful display.** Static and flicker-free, ~5 mA/segment, showing 0–F
  with clean uppercase B and D (not the 7-seg lowercase `b`/`d` compromise).
- **One modern part where the original used a hybrid.** The PIC16F13145's CLB
  latches the data bus in hard real time (< 6 ns), and the CPU only decodes —
  the timing-critical part lives in hardware, out of the CPU's hands.
- **Simple to build.** SMD LEDs on the front, the PIC and passives on the back,
  no level shifting (both parts are 5 V TTL), no LED driver chip.

## What's here

- `DESIGN.md` — the full board design: pinouts, the two-part match-up, pin
  assignment, BOM, form factor.
- `font.h` — the 16-entry hex decode table and the segment→pin map.
- `CLB.md` — the CLB latch design (the transparent-latch topology).

## Status

Design and firmware sketches are drafted; nothing is built yet. The open items
are the exact 11-segment glyph geometry, the interface style (header vs DIP
rows vs castellated edges), and confirming the boardlet form factor for the
target equipment.
