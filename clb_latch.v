// clb_latch.v — TIL311 clone CLB design (compiled by MCC's CLB synthesizer)
//
// Four transparent latches, one per data bit: transparent while the strobe is
// LOW, frozen on the strobe's rising edge — matching the TIL311.
//
// Each transparent latch is a mux + flip-flop:
//       q <= (strobe) ? q : data;     // clocked by HFINTOSC
//
// ---------------------------------------------------------------------------
// INPUT ROUTING — the one real constraint
//
// This part exposes only four CLB *pin* inputs, CLBIN0-3 (see the pin
// allocation table: RA2/RC3/RB4/RB5).  The four data bits fill them, so the
// strobe cannot be a fifth pin input.  Two ways in:
//
//   1. Transparent latch (this file) — route the strobe through a CLC: a CLC
//      input pin -> CLC output -> CLB internal input (the mux select).  The
//      CLC is a pass-through, but it is what buys the 5th input.  Faithful
//      live-through transparency.
//
//   2. Edge-triggered FF (simpler) — use the strobe as the CLB clock, and the
//      four latches become plain D-FFs:
//           q <= data;                 // clocked by the strobe (rising edge)
//      No CLC needed, but the display does not follow the data while the
//      strobe is held low — it only samples at the rising edge.
//
// Confirm the CLBIN count (4 vs more) against the datasheet's CLB chapter
// before choosing; this sketch assumes 4 and writes the transparent version.
// ---------------------------------------------------------------------------

module clb_latch (
    input  wire       clk,        // CLB clock (HFINTOSC) — free-running
    input  wire [3:0] data,       // A-D on CLBIN0-3 (data[0]=A ... data[3]=D)
    input  wire       strobe,     // latch strobe, via CLC (0=transparent, 1=hold)
    output reg  [3:0] q,          // latched nibble -> CLBSWINL (CPU reads it)
    output wire       irq         // strobe rising edge -> CLB1I0 (wakes CPU)
);

    // Four transparent latches.
    always @(posedge clk) begin
        q <= strobe ? q : data;
    end

    // Rising-edge detect for the interrupt.
    reg strobe_q;
    always @(posedge clk) begin
        strobe_q <= strobe;
    end
    assign irq = strobe & ~strobe_q;

endmodule
