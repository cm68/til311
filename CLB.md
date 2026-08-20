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

The CPU does **not** read the data pins — it reads the latched value. The
four `Q`s appear as CLB outputs; the CLB's output register is readable by the
CPU directly (no GPIO consumed), so the ISR does a single register read of the
four latched bits. (The exact register — a CLBOUT/software-read register — is
in the full datasheet's CLB section; this is the one thing to confirm against
DS40002486 rather than the product brief.)

## Getting the CPU's attention

The rising edge of the strobe must wake the CPU. Simplest is the **IOC**
(interrupt-on-change) on the strobe pin itself — the CLB doesn't need to
generate the interrupt. On the edge the CPU:

1. reads the four latched bits (CLB output register),
2. looks up `font[nibble]`,
3. writes the 11 segment pins.

There is no timing pressure in the ISR — the CLB has already frozen the data.

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

## Register values

The CLB is schematically programmed in **MCC's CLB synthesizer** (draw the four
latches, wire the strobe as the mux select and HFINTOSC as the clock), and MCC
emits the register settings. Hand-computing them is unnecessary and error-prone;
the topology above is what the schematic should show.
