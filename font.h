/*
 * TIL311 clone — 11-segment hex font.
 *
 * Segment bits (bit 0 = LSB of a 16-bit font value):
 *   aL aR  top bar split into left/right halves
 *   b  c   right verticals (upper/lower)
 *   dL dR  bottom bar split into left/right halves
 *   e  f   left verticals (lower/upper)
 *   g      middle bar
 *   h  i   right-side diagonals (the B/D curve)
 *
 * The split top/bottom bars are what give clean uppercase B and D:
 * B and D light only aL/dL (half-length), so the diagonal h/i forms the
 * curve instead of a full-width shoulder.
 */
#ifndef FONT_H
#define FONT_H

#include <stdint.h>

#define SEG_AL  0x001u  /* top-left half        */
#define SEG_AR  0x002u  /* top-right half       */
#define SEG_B   0x004u  /* upper-right          */
#define SEG_C   0x008u  /* lower-right          */
#define SEG_DL  0x010u  /* bottom-left half     */
#define SEG_DR  0x020u  /* bottom-right half    */
#define SEG_E   0x040u  /* lower-left           */
#define SEG_F   0x080u  /* upper-left           */
#define SEG_G   0x100u  /* middle               */
#define SEG_H   0x200u  /* upper-right diagonal */
#define SEG_I   0x400u  /* lower-right diagonal */

/* nibble (0x0..0xF) -> 11-bit segment pattern */
static const uint16_t font[16] = {
    0x0FF,  /* 0 */
    0x00C,  /* 1 */
    0x177,  /* 2 */
    0x13F,  /* 3 */
    0x18C,  /* 4 */
    0x1BB,  /* 5 */
    0x1FB,  /* 6 */
    0x00F,  /* 7 */
    0x1FF,  /* 8 */
    0x1BF,  /* 9 */
    0x1CF,  /* A */
    0x7D1,  /* B */
    0x0F3,  /* C */
    0x6D1,  /* D */
    0x1F3,  /* E */
    0x1C3,  /* F */
};

/*
 * Segment -> pin map (20-pin PDIP).  Each segment bit indexes this table;
 * `lat` is 0=LATA 1=LATB 2=LATC and `mask` the pin's bit within that port.
 *
 *   bit   seg  pin
 *   0     aL   RC2   LATC bit 2
 *   1     aR   RC6   LATC bit 6
 *   2     b    RC4   LATC bit 4
 *   3     c    RC5   LATC bit 5
 *   4     dL   RA1   LATA bit 1
 *   5     dR   RC7   LATC bit 7
 *   6     e    RA0   LATA bit 0
 *   7     f    RA4   LATA bit 4
 *   8     g    RA5   LATA bit 5
 *   9     h    RB6   LATB bit 6
 *   10    i    RB7   LATB bit 7
 *
 * RA0/RA1 double as ICSPDAT/ICSPCLK during programming; in normal
 * operation they are segment e and dL.
 */
typedef struct { uint8_t lat; uint8_t mask; } segpin_t;

static const segpin_t segpin[11] = {
    { 2, 1u<<2 },  /* aL -> LATC bit 2 (RC2) */
    { 2, 1u<<6 },  /* aR -> LATC bit 6 (RC6) */
    { 2, 1u<<4 },  /* b  -> LATC bit 4 (RC4) */
    { 2, 1u<<5 },  /* c  -> LATC bit 5 (RC5) */
    { 0, 1u<<1 },  /* dL -> LATA bit 1 (RA1) */
    { 2, 1u<<7 },  /* dR -> LATC bit 7 (RC7) */
    { 0, 1u<<0 },  /* e  -> LATA bit 0 (RA0) */
    { 0, 1u<<4 },  /* f  -> LATA bit 4 (RA4) */
    { 0, 1u<<5 },  /* g  -> LATA bit 5 (RA5) */
    { 1, 1u<<6 },  /* h  -> LATB bit 6 (RB6) */
    { 1, 1u<<7 },  /* i  -> LATB bit 7 (RB7) */
};

#endif /* FONT_H */
