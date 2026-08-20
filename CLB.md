# CLB latch — design notes

The part the CPU can't do is the latching: the data on A/B/C/D is only
guaranteed for a few tens of ns around the strobe, and the CPU's interrupt
latency is microseconds. The CLB does it in hardware (< 6 ns), and the CPU
reads the latched nibble whenever it gets around to it.

## What the latch has to do

The TIL311 latch is a **level-sensitive transparent latch**:

- strobe **low**  → the latches *follow* the data inputs (live).
- strobe **high** → the latches *hold* whatever was there at the rising edge.

Setup ≥ 50 ns before the rising edge, hold ≥ 40 ns after.

## Transparent latch from one BLE

Each Basic Logic Element is a 16-input LUT plus a D flip-flop. One transparent
latch is built from one BLE:

```
                 +--------+
  data (CLBINx)  |  LUT   |   D       Q
          ------>| 2:1    |------->[FF]----+----> CLBOUTx
          strobe | mux    |        ^       |
          ------>|        |        +-------+
                 +--------+            |
                    sel=strobe      (Q feedback)
```

The LUT is a 2:1 mux with the **strobe as select**:

- strobe = 0 → LUT output = `data`  (the FF follows the input, transparent)
- strobe = 1 → LUT output = `Q`     (the FF holds: D = its own Q)

The FF is clocked by the **free-running CLB clock** (HFINTOSC, or a divided
rate), so while strobe is low the latch tracks the data continuously. Four
BLEs, one per data bit, each with the same strobe as its mux select.

### Signals

| signal | pin | role |
|---|---|---|
| CLBIN0 | RA2 | data A (LSB) |
| CLBIN1 | RC3 | data B |
| CLBIN2 | RB4 | data C |
| CLBIN3 | RB5 | data D (MSB) |
| strobe | RC0 | mux select on all four latches |
| CLB clock | HFINTOSC | the continuous clock for transparency |
| CLBOUT0–3 | (internal) | the four latched bits |

CLB inputs are PPS-remappable, so A–D can sit on any four pins.

## Reading the latched nibble

The CPU does **not** read the data pins — it reads the latched value. The four
`Q`s are routed to the CLB's software output net, and the CPU reads them from
the low byte of the software-window register:

    nibble = CLBSWINL & 0x0F;

No GPIO consumed. `CLBSWINL` is the real symbol — the 32-bit software-window
register `CLBSWINL/M/H/U`, where writing injects a software input and reading
returns the software output.

## Getting the CPU's attention

The CLB has four interrupt outputs, `CLB1I0..3` — one per logic group — flagged
and enabled via `PIR7bits.CLB1IFn` / `PIE7bits.CLB1IEn`. Wire the latch capture
(the strobe edge) to `CLB1I0` in the schematic and enable it; the ISR then:

1. clears `PIR7bits.CLB1IF0`,
2. reads `CLBSWINL & 0x0F`,
3. looks up `font[nibble]`, writes the 11 segment pins.

There is no timing pressure in the ISR — the CLB has already frozen the data.
(The strobe pin's IOC would also work and skips the schematic wiring, at the
cost of a separate IOC configuration.)

## Simpler alternative: edge-triggered D-FFs

If live transparency is not required (most TIL311 circuits pulse the strobe
rather than holding it low), the latch can be reduced to four **edge-triggered
D flip-flops** clocked by the strobe's rising edge — D = data, clock = strobe.
That drops the mux/feedback and the free-running clock, and captures the data
on the rising edge. It is not transparent (no live-through while strobe low),
but it is the same capture point and uses the same four BLEs.

## BLE budget

Four BLEs of the 32 are used (one per bit), with or without the mux. The rest
of the fabric is free — e.g. a spare BLE could gate the segment drive off the
blanking input for hardware PWM dimming, and the 3-bit counter is available
if a multiplexed drive were ever wanted.

## Register names

Confirmed from the part's MCC-generated CLB driver (Microchip's own, generated
from the datasheet):

| register | role |
|---|---|
| `CLBCON` | control — `CLBEN` enable, `BUSY` bitstream load |
| `CLBCLK` | clock source select |
| `CLBPPSCON1..4` | output enable select `OESEL0..7` (PPS to pins) |
| `CLBSWINL/M/H/U` | 32-bit software window — write input, read output |
| `PIR7` / `PIE7` | `CLB1IF0..3` flags / `CLB1IE0..3` enables |

Global enables are `INTCONbits.GIE` / `INTCONbits.PEIE`.

The CLB is schematically programmed in **MCC's CLB synthesizer** (draw the four
latches, wire the strobe as the mux select and HFINTOSC as the clock), and MCC
emits the register settings. Hand-computing them is unnecessary and error-prone;
the topology above is what the schematic should show.
