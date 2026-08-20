/*
 * til311.c — TIL311 clone firmware sketch (PIC16F13145)
 *
 * The CLB is configured (in MCC) as four transparent latches: data A-D on
 * CLBIN0-3, the strobe as the latch enable, HFINTOSC as the free-running
 * clock, and the four latched bits on CLBOUT0-3.  This file is everything the
 * CPU does: on the strobe's edge it reads the frozen nibble and decodes it to
 * the 11 segments.
 *
 * This is a sketch — the register and vector names below follow the usual
 * PIC16F1xxx conventions and must be matched to this part's header (the CLB
 * output register especially: see DS40002486).
 */

#include <xc.h>
#include "font.h"

/* ---- CLB latch ---- */
/* CLBOUT0..3 hold latched A..D (nibble = D<<3 | C<<2 | B<<1 | A).
 * The exact read register is the one thing to confirm against the CLB
 * chapter of DS40002486. */
#define CLB_NIBBLE   CLBOUT          /* placeholder */

static uint8_t clb_read_nibble(void)
{
    return (uint8_t)(CLB_NIBBLE & 0x0F);
}

/* ---- display ---- */
static volatile uint8_t current;     /* last digit, so blanking can restore */

/* Decode a nibble and write the 11 segments across LATA/LATB/LATC. */
static void display(uint8_t nibble)
{
    uint16_t m = font[nibble & 0x0F];
    uint8_t a = 0, b = 0, c = 0;
    uint8_t i;

    for (i = 0; i < 11; i++) {
        if (m & (1u << i)) {
            switch (segpin[i].lat) {
            case 0: a |= segpin[i].mask; break;
            case 1: b |= segpin[i].mask; break;
            case 2: c |= segpin[i].mask; break;
            }
        }
    }
    LATA = a;
    LATB = b;
    LATC = c;
    current = nibble & 0x0F;
}

/* Blanking is active-high and does not disturb the latch, so unblanking
 * restores the digit that is still stored. */
static void blank(uint8_t on)
{
    if (on) {
        LATA = 0;
        LATB = 0;
        LATC = 0;
    } else {
        display(current);
    }
}

/* ---- interrupts ---- */
/* One ISR covers both the strobe and the blanking input.  If the CLB is set
 * up to generate the interrupt instead of (or in addition to) the strobe's
 * IOC, the body is identical: read the latch, decode, display. */
void __interrupt() isr(void)
{
    /* Strobe (RC0) rising edge: the CLB has frozen the bus. */
    if (IOCCF & 0x01) {
        IOCCF &= ~0x01;
        display(clb_read_nibble());
    }
    /* Blank (RC1) both edges: high blanks, low restores. */
    if (IOCCF & 0x02) {
        IOCCF &= ~0x02;
        blank((uint8_t)RC1);
    }
}

/* ---- setup ---- */
void main(void)
{
    /* All pins digital (the ADCC analog mux defaults to analog). */
    ANSELA = 0;
    ANSELB = 0;
    ANSELC = 0;

    /* Directions.  Inputs: data A-D, strobe, blank.  Outputs: 11 segments. */
    TRISA = 0x0C;     /* RA0(e) RA1(dL) RA4(f) RA5(g) out, RA2(data A) in */
    TRISB = 0x30;     /* RB6(h) RB7(i) out, RB4(data C) RB5(data D) in */
    TRISC = 0x0B;     /* RC2/4/5/6/7 segs out, RC0(strobe) RC1(blank) RC3(B) in */
    LATA = 0;
    LATB = 0;
    LATC = 0;

    /* Interrupt-on-change: strobe on the rising edge only (that is the latch
     * point), blank on both edges (so PWM dimming is followed). */
    IOCCP = 0x03;     /* positive edge on RC0 and RC1 */
    IOCCN = 0x02;     /* negative edge on RC1 only */
    IOCCF = 0;        /* clear any stale flags */

    /* Enable the IOC interrupt and the global enables. */
    IOCIE = 1;
    PEIE = 1;
    GIE = 1;

    display(0);       /* power-up shows 0 until the first strobe */

    for (;;) {
        /* The CLB does the real-time work; the CPU sleeps between strobes. */
        SLEEP();
    }
}
