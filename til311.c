/*
 * til311.c — TIL311 clone firmware sketch (PIC16F13145)
 *
 * The CLB is configured (in MCC) as four transparent latches: data A-D on
 * CLBIN0-3, the strobe as the latch enable, HFINTOSC as the free-running
 * clock, and the four latched bits on the software output net.  On the
 * strobe's edge the CLB also drives its interrupt (CLB1I0), which wakes the
 * CPU; the CPU reads the frozen nibble and decodes it to the 11 segments.
 *
 * Register names below come from Microchip's own MCC-generated CLB driver for
 * this part, so CLBCON/CLBCLK/CLBPPSCON/CLBSWIN/PIR7/PIE7 are the real
 * symbols; the interrupt vector (vectored controller) is the one thing left
 * to match against xc.h.
 */

#include <xc.h>
#include "font.h"

/* ---- CLB latch ---- */
/* The four latched bits (A-D, nibble = D<<3 | C<<2 | B<<1 | A) are read from
 * the CLB software interface register, low byte.  The CLB design must route
 * the latch outputs to the software output net (done in the MCC schematic). */
static uint8_t clb_read_nibble(void)
{
    return (uint8_t)(CLBSWINL & 0x0F);
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

/* Blanking is active-high and does not disturb the latch. */
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

/* ---- interrupt ---- */
/* The CLB raises CLB1I0 when the latch captures; the handler reads the frozen
 * nibble and updates the segments.  (Blanking can ride a second CLB interrupt,
 * CLB1I1, or the blank pin's IOC — left for the schematic.) */
void __interrupt() isr(void)
{
    if (PIR7bits.CLB1IF0) {
        PIR7bits.CLB1IF0 = 0;
        display(clb_read_nibble());
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

    /* CLB latch interrupt (wired to the strobe edge in the MCC schematic). */
    PIR7bits.CLB1IF0 = 0;
    PIE7bits.CLB1IE0 = 1;

    /* Global enables. */
    INTCONbits.PEIE = 1;
    INTCONbits.GIE = 1;

    display(0);       /* power-up shows 0 until the first strobe */

    for (;;) {
        /* The CLB does the real-time work; the CPU sleeps between strobes. */
        SLEEP();
    }
}
