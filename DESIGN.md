# TIL311 clone — board design

A boardlet that reproduces the function of the Texas Instruments TIL311
hexadecimal display: 4 data lines + a latch strobe + a blanking line in, one
static 0–F digit out. The TIL311 is becoming scarce; this replaces it with a
PIC16F13145, whose on-chip Configurable Logic Block (CLB) captures the data
bus in hard real time and leaves the CPU to do the 4-bit → segment decode.

The digit is **11 segments + 2 decimal points** — thirteen surface-mount LEDs,
driven statically. Everything — LEDs, PIC, passives — is on one side of the
board (single-sided hotplate assembly), with the PIC tucked under the LED array
exactly like the original's hidden chip.

## Sources

- TIL311 datasheet — SODS001D (TI, 1972/1992). 14-pin DIP.
- PIC16F13145 Family Product Brief — DS40002486A (Microchip).

## The two parts

### TIL311 (14-pin DIP, 0.300 in wide; pins 6, 9, 11 omitted)

| Pin | Name | Function |
|---|---|---|
| 1  | LED V+ | LED supply (5 V), may be tied to logic VCC |
| 2  | Data B | latch data, weight 2 |
| 3  | Data A | latch data, weight 1 (LSB) |
| 4  | Left DP cathode | decimal point, externally current-limited |
| 5  | Latch Strobe | **low** = transparent, **high** = hold |
| 7  | GND | common ground |
| 8  | Blanking | **high** = blanked, can be pulsed for dimming |
| 10 | Right DP cathode | decimal point, externally current-limited |
| 12 | Data D | latch data, weight 8 (MSB) |
| 13 | Data C | latch data, weight 4 |
| 14 | Logic VCC | 5 V |

Electrical / timing:

- Logic VCC 4.5–5.5 V, LED supply 4–5.5 V. Inputs TTL: V~IH~ ≥ 2 V, V~IL~ ≤ 0.8 V.
- Latch strobe: pulse ≥ 40 ns, setup ≥ 50 ns, hold ≥ 40 ns.
- The original digit is a 4 × 7 dot matrix (28 dots); the clone uses an
  11-segment font instead — functionally identical, cosmetically simpler.
- Constant-current drive, ≈ 5 mA per segment. Logic supply current 60–90 mA.
- Decimal points: anodes to LED V+, cathodes to pins 4/10, **no internal limiting**
  (external resistor required) — not decoded, latched, or blanked.

### PIC16F13145 (20-pin; the VQFN-20 3×3, ordering code `-I/REB`)

- 1.8–5.5 V operation → **runs at 5 V, directly TTL-compatible.**
- 17 I/O + MCLR (input-only). 14 KB flash, 1 KB RAM, 32 MHz.
- **CLB**: 32 Basic Logic Elements, each a 16-input LUT + one flip-flop, plus a
  dedicated 3-bit hardware counter. Propagation < 6 ns. CPU-independent.
- CLB inputs `CLBIN0–3`, outputs `CLBOUT0–7`, routed to pins via **PPS**.
- Interrupt-on-change (IOC) on every pin.

## Match-up: the key findings

1. **Levels match — no translation needed.** Both parts are 5 V TTL; the PIC
   runs at 5.5 V max and its TTL input threshold covers the TIL311's V~IH~/V~IL~.
2. **Timing is met easily.** The TIL311 demands 40–50 ns setup/hold; the CLB
   latches in < 6 ns, independent of the CPU.
3. **Package mismatch — this is a boardlet, not a drop-in.** The PIC16F13145 is
   20-pin only; the TIL311 is 14-pin DIP. The clone carries the TIL311's
   *signal interface* on its own footprint. (A true 14-pin drop-in would need
   the sibling PIC16F13125 and a serial LED driver — the 11-segment digit uses
   17 pins, far more than the 14-pin part's 11 I/O.)

## Architecture

```
  A ──┐
  B ──┤   ┌───────────── CLB ─────────────┐
  C ──┼──▶  4 transparent latches          │
  D ──┘      (strobe = latch-enable)       │
  STROBE ──────────────────────────────────┼──▶ CPU (IOC interrupt)
  BLANK ───────────────────────────────────┼──▶ CPU / display enable
             │                             │
             └── latched nibble ───────────┘ (read by CPU)
                                            │
                                  CPU decodes 4→11 segments
                                            │
                                11 segment LEDs (direct drive)
```

- **CLB**: four BLEs as transparent latches (D through when strobe low, hold
  when strobe high), one per data bit — mirroring the TIL311's latch exactly,
  so short-lived bus data is captured in < 6 ns.
- **CPU**: the strobe pin's IOC fires an interrupt; the handler reads the
  latched nibble, decodes it, and writes the 11 segment pins. Decode is a
  16-entry table; there is no timing pressure between strobes.

## The digit

Eleven segments: the 7-seg core with the top and bottom bars each split into a
left and right half, plus the two right-side diagonals. Splitting the bars is
what makes B and D look right — it lets them use a *half-length* top and bottom
(the left half), so the diagonal forms the curve instead of a full-width
shoulder. Each segment is one GPIO through one series resistor (≈ 5 mA at 5 V,
~560–680 Ω depending on the LED's V~f~), static, no multiplexing.

The two decimal points are two more SMD LEDs, kept **passive** exactly like the
original: anode to +5 V, cathode to the DP pin, external series resistor.

## The 0–F glyphs

Segment letters: `aL`/`aR` top halves, `b`/`c` right verticals, `dL`/`dR` bottom
halves, `e`/`f` left verticals, `g` middle, `h`/`i` right diagonals.

```
  0       1       2       3
┌───────┐               ┌───────┐   ┌───────┐
│       │           │           │           │
│       │           │           │           │
                        ├───────┤   ────────┤
│       │           │   │                   │
│       │           │   │                   │
└───────┘               └───────┘   └───────┘

  4       5       6       7
            ┌───────┐   ┌───────┐   ┌───────┐
│       │   │           │                   │
│       │   │           │                   │
├───────┤   ├───────┤   ├───────┤
        │           │   │       │           │
        │           │   │       │           │
            └───────┘   └───────┘

  8       9       A       B
┌───────┐   ┌───────┐   ┌───────┐   ┌────
│       │   │       │   │       │   │     ╱
│       │   │       │   │       │   │      ╱
├───────┤   ├───────┤   ├───────┤   ├────────
│       │           │   │       │   │      ╲
│       │           │   │       │   │     ╲
└───────┘   └───────┘               └────

  C       D       E       F
┌───────┐   ┌────       ┌───────┐   ┌───────┐
│           │     ╱     │           │
│           │      ╱    │           │
                        ├────────   ├────────
│           │      ╲    │           │
│           │     ╲     │           │
└───────┘   └────       └───────┘
```

Decode table (segments lit):

| hex | segments | hex | segments |
|---|---|---|---|
| 0 | aL aR b c dL dR e f | 8 | aL aR b c dL dR e f g |
| 1 | b c | 9 | aL aR b c dL dR f g |
| 2 | aL aR b g e dL dR | A | aL aR b c e f g |
| 3 | aL aR b g c dL dR | B | aL dL e f g h i |
| 4 | f g b c | C | aL aR dL dR e f |
| 5 | aL aR f g c dL dR | D | aL dL e f h i |
| 6 | aL aR f g e c dL dR | E | aL aR dL dR e f g |
| 7 | aL aR b c | F | aL aR e f g |

## Form factor

Single-sided, like the original: the TIL311 hides its TTL chip under the LED
array, and this does the same.

- **One side only.** All parts — the VQFN PIC, the 13 SMD LEDs, the 11 segment
  resistors, decoupling, the MCLR pull-up — sit on the top face, so the board
  is a one-pass hotplate reflow with nothing on the back.
- **The PIC sits under the LED array.** The 3 × 3 mm VQFN is small enough to
  hide behind the digit, so the LEDs surround and cover it — the chip is
  invisible from the front, exactly as on a TIL311.
- **Interface on the edge.** The 11 TIL311 signals (A/B/C/D, strobe, blank,
  2 DP, 5 V, GND) come off as half-moon **castellations** or a row of
  **through-hole pins**, either of which lets the boardlet sit where a TIL311
  was.
- **ICSP** pads on the top face, used once at programming time.

The DP resistors stay off-board, exactly as they are with a real TIL311.

## Pin assignment (20-pin VQFN — pin names/numbers identical to the PDIP)

| PIC pin | Name | Connects to |
|---|---|---|
| 1  | VDD | +5 V (bus logic VCC) |
| 20 | VSS | GND |
| 4  | MCLR/RA3 | ICSP header (10 kΩ to VDD) |
| 17 | RA2 / CLBIN0 | Data A (LSB) |
| 7  | RC3 / CLBIN1 | Data B |
| 13 | RB4 / CLBIN2 | Data C |
| 12 | RB5 / CLBIN3 | Data D (MSB) |
| 16 | RC0 | Latch Strobe (CLB latch-enable + IOC) |
| 15 | RC1 | Blanking (IOC; optionally CLB-gated for PWM dim) |
| 14 | RC2 | segment aL (top-left half) |
| 8  | RC6 | segment aR (top-right half) |
| 6  | RC4 | segment b (upper-right) |
| 5  | RC5 | segment c (lower-right) |
| 18 | RA1 | segment dL (bottom-left half) |
| 9  | RC7 | segment dR (bottom-right half) |
| 19 | RA0 | segment e (lower-left) |
| 3  | RA4 | segment f (upper-left) |
| 2  | RA5 | segment g (middle) |
| 11 | RB6 | segment h (upper-right diagonal) |
| 10 | RB7 | segment i (lower-right diagonal) |
| —  | DP L / DP R | two SMD LEDs, anode +5 V, cathode to the two DP header pins |

Six inputs + 11 segments = **17 of 17 GPIO**, all used. CLB inputs are
PPS-remappable; RA0/RA1 double as ICSPDAT/ICSPCLK during programming. The
segment-to-pin assignment is arbitrary and can be permuted for the PCB.

## BOM (one digit)

- 1 × PIC16F13145-I/REB (20-pin VQFN, 3 × 3 × 0.9 mm, exposed pad to VSS)
- 11 × SMD red LEDs (segments) + 2 × SMD red LEDs (decimal points)
- 11 × segment series resistors (~560–680 Ω), 2 × DP series resistors (external)
- 1 × 0.1 µF + 1 × 10 µF decoupling on VDD; 10 kΩ on MCLR
- 1 × 5-pin ICSP header

## Firmware outline

1. **CLB config** (MCC): four BLEs as transparent latches, strobe on the
   latch-enable, outputs to CLBOUT0–3.
2. **IOC** on the strobe pin → interrupt handler.
3. Handler: read the latched nibble (CLB output/status register), look up the
   11-bit segment pattern (16-entry table), write the segment GPIOs.
4. Blanking: on the blank pin's IOC, blank the segments (or gate in the CLB if
   PWM dimming is wanted).

## Still to pin down

- **The 11-segment glyph geometry** — the exact diagonal placement and bar-split
  point. The table above is a starting point; eyeball B and D on the real board
  and tune the diagonal position and direction until they read cleanly.
- **Confirm the VQFN size.** The product brief lists the 20-pin VQFN as 4 × 4 mm,
  but the `-I/REB` distributor entry says 3 × 3 mm — verify the "Packaging
  Information" section of the full datasheet before ordering.
- **Castellations vs through-hole** — pick one for the edge interface when the
  target footprint is known.
