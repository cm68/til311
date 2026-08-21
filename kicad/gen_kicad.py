#!/usr/bin/env python3
"""Generate a KiCad 9 project (schematic + PCB skeleton) for the TIL311 clone.

Writes into the current directory:
  til311.kicad_pro, til311.kicad_sym, til311.kicad_sch, til311.kicad_pcb,
  sym-lib-table, fp-lib-table
"""
import os, uuid

def U():
    return str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Symbols.  A pin is (number, name, etype, tip_x, tip_y, angle, length).
# In KiCad the pin's (at x y angle) IS the connection point (the tip); the
# body extends from there by `length` in the direction of `angle`
# (0 = +x/right, 90 = +y/up, 180 = -x/left, 270 = -y/down).
# ---------------------------------------------------------------------------
ETYPE = {
    'pwr_in': 'power_in', 'pwr_out': 'power_out', 'bi': 'bidirectional',
    'in': 'input', 'out': 'output', 'pass': 'passive', 'nc': 'no_connect',
}

def conn(pin):
    return (pin[3], pin[4])   # tip is the connection point

# PIC16F13145 — 20 pins, 1-10 left, 11-20 right; body x 0..15.24
PIC_PINS = []
for i in range(1, 11):     # left pins: tip at x=-5.08, body extends right
    PIC_PINS.append((i, f"P{i}", "bi", -5.08, -(i-1)*2.54, 0, 5.08))
for i in range(11, 21):    # right pins: tip at x=20.32, body extends left
    PIC_PINS.append((i, f"P{i}", "bi", 20.32, -(i-11)*2.54, 180, 5.08))
PIC_NAMES = {
    1: "VDD", 2: "RA5", 3: "RA4", 4: "MCLR", 5: "RC5", 6: "RC4", 7: "RC3",
    8: "RC6", 9: "RC7", 10: "RB7", 11: "RB6", 12: "RB5", 13: "RB4", 14: "RC2",
    15: "RC1", 16: "RC0", 17: "RA2", 18: "RA1", 19: "RA0", 20: "VSS",
}
PIC_ETYPE = {1: "pwr_in", 4: "in", 20: "pwr_in"}
PIC_PINS = [(n, PIC_NAMES[n], PIC_ETYPE.get(n, "bi"),
             x, y, a, L) for (n, _n, _e, x, y, a, L) in PIC_PINS]

# simple 2-pin passive (R, C) and LED
def two_pin(names, etypes):
    return [(1, names[0], etypes[0], -5.08, 0, 0, 2.54),
            (2, names[1], etypes[1],  5.08, 0, 180, 2.54)]

R_PINS  = two_pin(("1", "2"), ("pass", "pass"))
C_PINS  = two_pin(("1", "2"), ("pass", "pass"))
LED_PINS = two_pin(("K", "A"), ("pass", "pass"))

# connectors
def conn_1xN(N):
    return [(i, f"Pin_{i}", "pass", -5.08, -(i-1)*2.54, 0, 2.54) for i in range(1, N+1)]
def conn_2xN(N):
    pins = []
    for row in range(N):
        pins.append((row*2+1, f"Pin_{row*2+1}", "pass", -5.08, -row*2.54, 0, 2.54))
        pins.append((row*2+2, f"Pin_{row*2+2}", "pass", 7.62, -row*2.54, 180, 2.54))
    return pins

SYMBOLS = {
    "PIC16F13145": (PIC_PINS, 15.24, 22.86),
    "R":           (R_PINS, 5.08, 2.54),
    "C":           (C_PINS, 5.08, 2.54),
    "LED":         (LED_PINS, 5.08, 2.54),
    "CONN_1x05":   (conn_1xN(5), 2.54, 10.16),
    "CONN_2x07":   (conn_2xN(7), 2.54, 15.24),
    "PWR_FLAG":    ([(1, "PWR_FLAG", "pwr_out", -2.54, 0, 0, 2.54)], 2.54, 2.54),
}

def emit_pin(p):
    n, name, et, x, y, a, L = p
    return (f'\t\t\t(pin {ETYPE[et]} line (at {x:.2f} {y:.2f} {a}) '
            f'(length {L:.2f})\n\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))\n'
            f'\t\t\t\t(number "{n}" (effects (font (size 1.27 1.27)))))\n')

def emit_symbol(libname, sname):
    pins, w, h = SYMBOLS[sname]
    s = f'\t\t(symbol "{libname}:{sname}"\n'
    s += f'\t\t\t(exclude_from_sim no)\n\t\t\t(in_bom yes)\n\t\t\t(on_board yes)\n'
    s += f'\t\t\t(property "Reference" "U" (at 0 {h/2+2.54:.2f} 0) (effects (font (size 1.27 1.27))))\n'
    s += f'\t\t\t(property "Value" "{sname}" (at 0 {-h/2-2.54:.2f} 0) (effects (font (size 1.27 1.27))))\n'
    s += f'\t\t\t(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
    s += f'\t\t\t(symbol "{sname}_0_1"\n'
    # body rectangle
    x0, y0 = 0, 0
    s += f'\t\t\t\t(rectangle (start {x0:.2f} {y0:.2f}) (end {w:.2f} {-h:.2f}) (stroke (width 0.254) (type default)) (fill (type background)))\n'
    for p in pins:
        s += emit_pin(p)
    s += '\t\t\t)\n\t\t)\n'
    return s

# ---------------------------------------------------------------------------
# Schematic netlist
# ---------------------------------------------------------------------------
# components: ref, symbol, x, y, [ (pin_number, net) ]
COMP = []

# PIC U1
pic = ("U1", "PIC16F13145", 0, 0)
pic_nets = {1:"+5V", 2:"SEG_g", 3:"SEG_f", 4:"nRST", 5:"SEG_c", 6:"SEG_b",
            7:"DATA_B", 8:"SEG_aR", 9:"SEG_dR", 10:"SEG_i", 11:"SEG_h",
            12:"DATA_D", 13:"DATA_C", 14:"SEG_aL", 15:"BLANK", 16:"STROBE",
            17:"DATA_A", 18:"SEG_dL", 19:"SEG_e", 20:"GND"}
COMP.append((pic[0], pic[1], pic[2], pic[3], pic_nets))

# segments: name -> (pic net, ref prefixes)
SEGS = [("aL","SEG_aL"),("aR","SEG_aR"),("b","SEG_b"),("c","SEG_c"),
        ("dL","SEG_dL"),("dR","SEG_dR"),("e","SEG_e"),("f","SEG_f"),
        ("g","SEG_g"),("h","SEG_h"),("i","SEG_i")]

# 11 resistors + 11 LEDs, in two columns (6 + 5) so nothing overlaps
for k, (seg, snet) in enumerate(SEGS, start=1):
    col = (k-1) // 6
    row = (k-1) % 6
    rx = 40.0 + col * 20.0
    lx = 55.0 + col * 20.0
    ry = -row * 7.62
    rref = f"R{k}"; lref = f"D{k}"
    COMP.append((rref, "R", rx, ry, {1: snet, 2: f"LED_{seg}"}))
    COMP.append((lref, "LED", lx, ry, {2: f"LED_{seg}", 1: "GND"}))

# 2 DP LEDs: anode -> +5V, cathode -> DP_L / DP_R
COMP.append(("D12", "LED", 75.0, 0, {2: "+5V", 1: "DP_L"}))
COMP.append(("D13", "LED", 75.0, -7.62, {2: "+5V", 1: "DP_R"}))

# decoupling caps + MCLR pull-up
COMP.append(("C1", "C", 8.0, 20.0, {1: "+5V", 2: "GND"}))
COMP.append(("C2", "C", 8.0, 12.0, {1: "+5V", 2: "GND"}))
COMP.append(("R12", "R", -8.0, -26.0, {1: "+5V", 2: "nRST"}))

# ICSP header J1 (1x5): VPP, VDD, GND, DAT(RA0=SEG_e), CLK(RA1=SEG_dL)
COMP.append(("J1", "CONN_1x05", -30.0, 10.0,
             {1:"nRST", 2:"+5V", 3:"GND", 4:"SEG_e", 5:"SEG_dL"}))

# Interface header J2 (2x7, TIL311 pinout)
COMP.append(("J2", "CONN_2x07", -30.0, -10.0,
             {1:"+5V", 2:"DATA_B", 3:"DATA_A", 4:"DP_L", 5:"STROBE", 6:"NC",
              7:"GND", 8:"BLANK", 9:"NC", 10:"DP_R", 11:"NC", 12:"DATA_D",
              13:"DATA_C", 14:"+5V"}))

# power flags (mark the externally-driven +5V and GND nets)
COMP.append(("FL1", "PWR_FLAG", 8.0, 24.0, {1: "+5V"}))
COMP.append(("FL2", "PWR_FLAG", 8.0, -28.0, {1: "GND"}))

# ---------------------------------------------------------------------------
# Emit schematic
# ---------------------------------------------------------------------------
def emit_sch():
    s = '(kicad_sch\n\t(version 20250114)\n\t(generator "eeschema")\n'
    s += '\t(generator_version "9.0")\n'
    s += f'\t(uuid "{U()}")\n\t(paper "A4")\n'
    s += '\t(title_block\n\t\t(title "TIL311 clone boardlet")\n'
    s += '\t\t(date "2026-08-20")\n\t\t(rev "0")\n\t\t(company "Curt Mayer")\n\t)\n'
    # lib_symbols
    s += '\t(lib_symbols\n'
    for sname in SYMBOLS:
        s += emit_symbol("til311", sname)
    s += '\t)\n'
    # symbol instances
    for ref, sname, x, y, nets in COMP:
        pins, w, h = SYMBOLS[sname]
        s += f'\t(symbol (lib_id "til311:{sname}") (at {x:.2f} {y:.2f} 0) (unit 1)\n'
        s += '\t\t(in_bom yes) (on_board yes) (dnp no)\n'
        s += f'\t\t(uuid "{U()}")\n'
        s += f'\t\t(property "Reference" "{ref}" (at {x:.2f} {y+5.0:.2f} 0) (effects (font (size 1.27 1.27))))\n'
        s += f'\t\t(property "Value" "{sname}" (at {x:.2f} {y-5.0:.2f} 0) (effects (font (size 1.27 1.27))))\n'
        s += f'\t\t(property "Footprint" "" (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) hide))\n'
        s += f'\t\t(instances (project "" (path "/" (reference "{ref}") (unit 1))))\n'
        for p in pins:
            n = p[0]
            s += f'\t\t(pin "{n}" (uuid "{U()}"))\n'
        s += '\t)\n'
    # global labels
    for ref, sname, x, y, nets in COMP:
        pins, w, h = SYMBOLS[sname]
        for p in pins:
            n = p[0]
            net = nets.get(n)
            if net is None or net == "NC":
                continue
            cx, cy = conn(p)
            gx, gy = x + cx, y + cy
            s += f'\t(global_label "{net}" (shape passive) (at {gx:.2f} {gy:.2f} 0) (effects (font (size 1.27 1.27))) (uuid "{U()}"))\n'
    s += ')\n'
    return s

# ---------------------------------------------------------------------------
# Emit project / lib tables / PCB skeleton
# ---------------------------------------------------------------------------
def emit_pro():
    return ('{\n'
            '  "board": {},\n'
            '  "meta": {\n'
            '    "filename": "til311.kicad_pro",\n'
            '    "version": 1\n'
            '  },\n'
            '  "net_settings": {\n'
            '    "classes": [],\n'
            '    "meta": {"version": 3},\n'
            '    "nets": []\n'
            '  },\n'
            '  "pcbnew": {"last_paths": {}},\n'
            '  "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []}\n'
            '}\n')

def emit_sym_lib_table():
    return ('(sym_lib_table\n'
            '  (version 7)\n'
            '  (lib (name "til311")(type "KiCad")(uri "${KIPRJMOD}/til311.kicad_sym")(options "")(descr ""))\n'
            ')\n')

def emit_fp_lib_table():
    return ('(fp_lib_table\n  (version 7)\n)\n')

def emit_sym():
    s = '(kicad_symbol_lib\n\t(version 20220914)\n\t(generator "gen_kicad")\n'
    for sname in SYMBOLS:
        s += emit_symbol("til311", sname)
    s += ')\n'
    return s

LAYERS = [
    (0, 'F.Cu', 'signal'), (2, 'B.Cu', 'signal'),
    (9, 'F.Adhes', 'user', 'F.Adhesive'), (11, 'B.Adhes', 'user', 'B.Adhesive'),
    (13, 'F.Paste', 'user'), (15, 'B.Paste', 'user'),
    (5, 'F.SilkS', 'user', 'F.Silkscreen'), (7, 'B.SilkS', 'user', 'B.Silkscreen'),
    (1, 'F.Mask', 'user'), (3, 'B.Mask', 'user'),
    (17, 'Dwgs.User', 'user', 'User.Drawings'), (19, 'Cmts.User', 'user', 'User.Comments'),
    (21, 'Eco1.User', 'user', 'User.Eco1'), (23, 'Eco2.User', 'user', 'User.Eco2'),
    (25, 'Edge.Cuts', 'user'), (27, 'Margin', 'user'),
    (31, 'F.CrtYd', 'user', 'F.Courtyard'), (29, 'B.CrtYd', 'user', 'B.Courtyard'),
    (35, 'F.Fab', 'user'), (33, 'B.Fab', 'user'),
    (39, 'User.1', 'back'), (41, 'User.2', 'user'), (43, 'User.3', 'user'), (45, 'User.4', 'user'),
]

def emit_pcb():
    s = '(kicad_pcb\n\t(version 20241229)\n\t(generator "pcbnew")\n\t(generator_version "9.0")\n'
    s += '\t(general\n\t\t(thickness 1.6)\n\t\t(legacy_teardrops no)\n\t)\n'
    s += '\t(paper "A4")\n'
    s += '\t(layers\n'
    for ln in LAYERS:
        if len(ln) == 3:
            i, name, typ = ln
            s += f'\t\t({i} "{name}" {typ})\n'
        else:
            i, name, typ, alias = ln
            s += f'\t\t({i} "{name}" {typ} "{alias}")\n'
    s += '\t)\n'
    s += '\t(setup\n\t\t(stackup\n'
    s += '\t\t\t(layer "F.SilkS" (type "Top Silk Screen"))\n'
    s += '\t\t\t(layer "F.Paste" (type "Top Solder Paste"))\n'
    s += '\t\t\t(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))\n'
    s += '\t\t\t(layer "F.Cu" (type "copper") (thickness 0.035))\n'
    s += '\t\t\t(layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))\n'
    s += '\t\t\t(layer "B.Cu" (type "copper") (thickness 0.035))\n'
    s += '\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))\n'
    s += '\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))\n'
    s += '\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen"))\n'
    s += '\t\t\t(copper_finish "None")\n\t\t\t(dielectric_constraints no)\n\t\t)\n'
    s += '\t\t(pad_to_mask_clearance 0)\n\t\t(allow_soldermask_bridges_in_footprints no)\n\t\t(tenting front back)\n'
    s += '\t\t(pcbplotparams\n'
    s += '\t\t\t(layerselection 0x00000000_00000000_55555555_5755f57f)\n'
    s += '\t\t\t(plot_on_all_layers_selection 0x00000000_00000000_00000000_00000000)\n'
    s += '\t\t\t(disableapertmacros no)\n\t\t\t(usegerberextensions no)\n'
    s += '\t\t\t(usegerberattributes yes)\n\t\t\t(usegerberadvancedattributes yes)\n'
    s += '\t\t\t(creategerberjobfile yes)\n\t\t\t(dashed_line_dash_ratio 12.000000)\n'
    s += '\t\t\t(dashed_line_gap_ratio 3.000000)\n\t\t\t(svgprecision 4)\n'
    s += '\t\t\t(plotframeref no)\n\t\t\t(mode 1)\n\t\t\t(useauxorigin no)\n'
    s += '\t\t\t(hpglpennumber 1)\n\t\t\t(hpglpenspeed 20)\n\t\t\t(hpglpendiameter 15.000000)\n'
    s += '\t\t\t(pdf_front_fp_property_popups yes)\n\t\t\t(pdf_back_fp_property_popups yes)\n'
    s += '\t\t\t(pdf_metadata yes)\n\t\t\t(pdf_single_document no)\n'
    s += '\t\t\t(dxfpolygonmode yes)\n\t\t\t(dxfimperialunits yes)\n\t\t\t(dxfusepcbnewfont yes)\n'
    s += '\t\t\t(psnegative no)\n\t\t\t(psa4output no)\n\t\t\t(plot_black_and_white yes)\n'
    s += '\t\t\t(sketchpadsonfab no)\n\t\t\t(plotpadnumbers no)\n\t\t\t(hidednponfab no)\n'
    s += '\t\t\t(sketchdnponfab yes)\n\t\t\t(crossoutdnponfab yes)\n\t\t\t(subtractmaskfromsilk no)\n'
    s += '\t\t\t(outputformat 1)\n\t\t\t(mirror no)\n\t\t\t(drillshape 0)\n'
    s += '\t\t\t(scaleselection 1)\n\t\t\t(outputdirectory "")\n\t\t)\n\t)\n'
    s += '\t(net 0 "")\n'
    def gl(x1, y1, x2, y2):
        return ('\t(gr_line\n\t\t(start %.2f %.2f)\n\t\t(end %.2f %.2f)\n'
                '\t\t(stroke (width 0.2) (type default))\n'
                '\t\t(layer "Edge.Cuts")\n\t\t(uuid "%s")\n\t)\n') % (x1, y1, x2, y2, U())
    s += gl(-30, -17.5, 30, -17.5)
    s += gl(30, -17.5, 30, 17.5)
    s += gl(30, 17.5, -30, 17.5)
    s += gl(-30, 17.5, -30, -17.5)
    s += ('\t(gr_text "TIL311 clone" (at 0 0 0) (layer "F.SilkS") (uuid "%s")\n'
          '\t\t(effects (font (size 2 2) (thickness 0.3)))\n\t)\n') % U()
    s += '\t(embedded_fonts no)\n)\n'
    return s

# ---------------------------------------------------------------------------
out = os.getcwd()
def w(name, content):
    with open(os.path.join(out, name), "w") as f:
        f.write(content)
    print("wrote", name, len(content), "bytes")

w("til311.kicad_pro", emit_pro())
w("til311.kicad_sym", emit_sym())
w("til311.kicad_sch", emit_sch())
w("til311.kicad_pcb", emit_pcb())
w("sym-lib-table", emit_sym_lib_table())
w("fp-lib-table", emit_fp_lib_table())
print("done")
