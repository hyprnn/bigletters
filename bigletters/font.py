"""Fonts: a vector stroke font rendered through a distance field (smooth, crisp at any
size, any weight) plus the old 5x7 bitmap font for the 'pixel' style.

Glyph coordinates: x right, y down. A glyph box is [0, w] x [0, 6]; strokes have a
radius (the weight), so a glyph really covers [-r, w + r] x [-r, 6 + r] and one text
line is 7 units tall. The advance of a glyph is w + 2 (stroke margin + gap)."""
import math

FONT_NAMES = ["normal", "bold", "thin", "pixel", "italic", "wavy"]
RADIUS = {"normal": .55, "bold": .85, "thin": .3, "pixel": .5, "italic": .55, "wavy": .55}
SPACE_ADV = 3.0
LINE_H = 7.0
LINE_GAP = 2.0


def _arc(cx, cy, rx, ry, a0, a1):
    n = max(4, int(abs(a1 - a0) / 12))
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _p(*pts):
    return [(float(x), float(y)) for x, y in pts]


def _bowl(x0, y0, rx, ry, y_end):
    """a 'P' style bowl starting at (x0,y0): right-facing half ellipse down to y_end"""
    return _arc(x0 + rx, y0 + ry, rx, ry, -90, 90)


def _build():
    S = {}
    S['A'] = (4, [_p((0, 6), (2, 0), (4, 6)), _p((.85, 4.2), (3.15, 4.2))])
    S['B'] = (3.8, [_p((0, 0), (0, 6)),
                    _p((0, 0)) + _arc(2.3, 1.5, 1.4, 1.5, -90, 90) + _p((0, 3)),
                    _p((0, 3)) + _arc(2.4, 4.5, 1.4, 1.5, -90, 90) + _p((0, 6))])
    S['C'] = (4, [_arc(2, 3, 2, 3, -40, -320)])
    S['D'] = (3.8, [_p((0, 0), (0, 6)), _p((0, 0)) + _arc(1.4, 3, 2.4, 3, -90, 90) + _p((0, 6))])
    S['E'] = (3.6, [_p((3.6, 0), (0, 0), (0, 6), (3.6, 6)), _p((0, 3), (3, 3))])
    S['F'] = (3.6, [_p((3.6, 0), (0, 0), (0, 6)), _p((0, 3), (3, 3))])
    S['G'] = (4, [_arc(2, 3, 2, 3, -40, -360), _p((4, 3), (2.2, 3))])
    S['H'] = (4, [_p((0, 0), (0, 6)), _p((4, 0), (4, 6)), _p((0, 3), (4, 3))])
    S['I'] = (2.4, [_p((1.2, 0), (1.2, 6)), _p((0, 0), (2.4, 0)), _p((0, 6), (2.4, 6))])
    S['J'] = (3.2, [_p((3.2, 0)) + _arc(1.7, 4.2, 1.5, 1.8, 0, 150)])
    S['K'] = (4, [_p((0, 0), (0, 6)), _p((3.8, 0), (0, 3.5)), _p((1.3, 2.2), (4, 6))])
    S['L'] = (3.6, [_p((0, 0), (0, 6), (3.6, 6))])
    S['M'] = (4.4, [_p((0, 6), (0, 0), (2.2, 3.8), (4.4, 0), (4.4, 6))])
    S['N'] = (4, [_p((0, 6), (0, 0), (4, 6), (4, 0))])
    S['O'] = (4, [_arc(2, 3, 2, 3, 0, 360)])
    S['P'] = (3.8, [_p((0, 6), (0, 0), (2.1, 0)) + _arc(2.1, 1.65, 1.7, 1.65, -90, 90) + _p((0, 3.3))])
    S['Q'] = (4, [_arc(2, 3, 2, 3, 0, 360), _p((2.4, 4.2), (4, 6.4))])
    S['R'] = (4, [_p((0, 6), (0, 0), (2.1, 0)) + _arc(2.1, 1.65, 1.7, 1.65, -90, 90) + _p((0, 3.3)),
                  _p((1.9, 3.3), (4, 6))])
    S['S'] = (3.8, [_arc(1.9, 1.5, 1.9, 1.5, -30, -270) + _arc(1.9, 4.5, 1.9, 1.5, -90, 150)])
    S['T'] = (4, [_p((0, 0), (4, 0)), _p((2, 0), (2, 6))])
    S['U'] = (4, [_p((0, 0), (0, 3.8)) + _arc(2, 3.8, 2, 2.2, 180, 0) + _p((4, 0))])
    S['V'] = (4, [_p((0, 0), (2, 6), (4, 0))])
    S['W'] = (5, [_p((0, 0), (1.2, 6), (2.5, 2.4), (3.8, 6), (5, 0))])
    S['X'] = (4, [_p((0, 0), (4, 6)), _p((4, 0), (0, 6))])
    S['Y'] = (4, [_p((0, 0), (2, 3), (4, 0)), _p((2, 3), (2, 6))])
    S['Z'] = (4, [_p((0, 0), (4, 0), (0, 6), (4, 6))])
    S['0'] = (3.6, [_arc(1.8, 3, 1.8, 3, 0, 360), _p((1, 4.4), (2.6, 1.6))])
    S['1'] = (3.2, [_p((0, 1.4), (1.6, 0), (1.6, 6)), _p((0, 6), (3.2, 6))])
    S['2'] = (4, [_arc(2, 1.8, 2, 1.8, -180, 45) + _p((0, 6), (4, 6))])
    S['3'] = (3.8, [_arc(1.9, 1.5, 1.8, 1.5, -150, 90) + _arc(1.9, 4.5, 1.9, 1.5, -90, 150)])
    S['4'] = (4, [_p((3.2, 0), (0, 4.2), (4, 4.2)), _p((3.2, 0), (3.2, 6))])
    S['5'] = (3.8, [_p((3.6, 0), (.3, 0), (.1, 2.9)) + _arc(1.9, 4.2, 1.9, 1.8, -115, 150)])
    S['6'] = (4, [_arc(2, 4.2, 2, 1.8, 0, 360), _p((0, 4.2)) + _arc(2, 2.4, 2, 2.4, 180, 300)])
    S['7'] = (4, [_p((0, 0), (4, 0), (1.4, 6))])
    S['8'] = (3.8, [_arc(1.9, 1.5, 1.7, 1.5, 0, 360), _arc(1.9, 4.5, 1.9, 1.5, 0, 360)])
    S['9'] = (4, [_arc(2, 1.8, 2, 1.8, 0, 360), _p((4, 1.8), (4, 3.6)) + _arc(2, 3.6, 2, 2.4, 0, 120)])
    S['!'] = (0, [_p((0, 0), (0, 4)), _p((0, 5.6), (0, 5.6))])
    S['?'] = (3.2, [_arc(1.6, 1.7, 1.6, 1.7, -190, 45) + _p((1.5, 3.8), (1.5, 4.2)), _p((1.5, 5.6), (1.5, 5.6))])
    S['.'] = (0, [_p((0, 5.6), (0, 5.6))])
    S[','] = (.8, [_p((.6, 5.3), (0, 6.9))])
    S[':'] = (0, [_p((0, 1.9), (0, 1.9)), _p((0, 5.1), (0, 5.1))])
    S[';'] = (.8, [_p((.6, 1.9), (.6, 1.9)), _p((.6, 5.1), (0, 6.7))])
    S['-'] = (2.6, [_p((0, 3), (2.6, 3))])
    S['+'] = (3, [_p((0, 3), (3, 3)), _p((1.5, 1.5), (1.5, 4.5))])
    S['='] = (3, [_p((0, 2.2), (3, 2.2)), _p((0, 3.9), (3, 3.9))])
    S['*'] = (3, [_p((1.5, 1), (1.5, 5)), _p((0, 2), (3, 4)), _p((0, 4), (3, 2))])
    S['/'] = (3, [_p((0, 6), (3, 0))])
    S['#'] = (4, [_p((1.3, 0), (.8, 6)), _p((3.2, 0), (2.7, 6)), _p((0, 2), (4, 2)), _p((0, 4), (4, 4))])
    S['@'] = (4.4, [_arc(2.2, 3, 2.2, 3, -25, -335), _arc(2.2, 3, 1, 1.2, 0, 360), _p((3.2, 1.9), (3.2, 4))])
    S['('] = (1.2, [_arc(1.4, 3, 1.3, 3.2, 110, 250)])
    S[')'] = (1.2, [_arc(-.1, 3, 1.3, 3.2, -70, 70)])
    S['_'] = (4, [_p((0, 6.4), (4, 6.4))])
    S["'"] = (0, [_p((0, 0), (0, 1.7))])
    S['&'] = (4, [_p((4, 6), (.9, 2.3)) + _arc(1.9, 1.5, 1.2, 1.5, 150, 450) + _arc(1.9, 4.5, 1.9, 1.5, -90, -250) + _p((3.1, 4), (4, 4.6))])
    S['%'] = (4, [_p((0, 6), (4, 0)), _arc(.9, 1.2, .7, .9, 0, 360), _arc(3.1, 4.8, .7, .9, 0, 360)])
    S['$'] = (3.8, [_arc(1.9, 1.5, 1.9, 1.5, -30, -270) + _arc(1.9, 4.5, 1.9, 1.5, -90, 150), _p((1.9, -.4), (1.9, 6.4))])
    S['<'] = (3, [_p((3, .8), (0, 3), (3, 5.2))])
    S['>'] = (3, [_p((0, .8), (3, 3), (0, 5.2))])
    return S


STROKES = _build()

# ---- the old 5x7 bitmap font (the 'pixel' style); also defines which characters exist
GLYPHS = {
 'A': "01110 10001 10001 11111 10001 10001 10001", 'B': "11110 10001 10001 11110 10001 10001 11110",
 'C': "01110 10001 10000 10000 10000 10001 01110", 'D': "11110 10001 10001 10001 10001 10001 11110",
 'E': "11111 10000 10000 11110 10000 10000 11111", 'F': "11111 10000 10000 11110 10000 10000 10000",
 'G': "01110 10001 10000 10111 10001 10001 01111", 'H': "10001 10001 10001 11111 10001 10001 10001",
 'I': "01110 00100 00100 00100 00100 00100 01110", 'J': "00111 00010 00010 00010 00010 10010 01100",
 'K': "10001 10010 10100 11000 10100 10010 10001", 'L': "10000 10000 10000 10000 10000 10000 11111",
 'M': "10001 11011 10101 10101 10001 10001 10001", 'N': "10001 11001 10101 10011 10001 10001 10001",
 'O': "01110 10001 10001 10001 10001 10001 01110", 'P': "11110 10001 10001 11110 10000 10000 10000",
 'Q': "01110 10001 10001 10001 10101 10010 01101", 'R': "11110 10001 10001 11110 10100 10010 10001",
 'S': "01111 10000 10000 01110 00001 00001 11110", 'T': "11111 00100 00100 00100 00100 00100 00100",
 'U': "10001 10001 10001 10001 10001 10001 01110", 'V': "10001 10001 10001 10001 10001 01010 00100",
 'W': "10001 10001 10001 10101 10101 11011 10001", 'X': "10001 10001 01010 00100 01010 10001 10001",
 'Y': "10001 10001 01010 00100 00100 00100 00100", 'Z': "11111 00001 00010 00100 01000 10000 11111",
 '0': "01110 10001 10011 10101 11001 10001 01110", '1': "00100 01100 00100 00100 00100 00100 01110",
 '2': "01110 10001 00001 00010 00100 01000 11111", '3': "11110 00001 00001 01110 00001 00001 11110",
 '4': "00010 00110 01010 10010 11111 00010 00010", '5': "11111 10000 11110 00001 00001 10001 01110",
 '6': "00110 01000 10000 11110 10001 10001 01110", '7': "11111 00001 00010 00100 01000 01000 01000",
 '8': "01110 10001 10001 01110 10001 10001 01110", '9': "01110 10001 10001 01111 00001 00010 01100",
 '!': "00100 00100 00100 00100 00100 00000 00100", '?': "01110 10001 00001 00010 00100 00000 00100",
 '.': "00000 00000 00000 00000 00000 01100 01100", ',': "00000 00000 00000 00000 01100 00100 01000",
 ':': "00000 01100 01100 00000 01100 01100 00000", ';': "00000 01100 01100 00000 01100 00100 01000",
 '-': "00000 00000 00000 11111 00000 00000 00000", '+': "00000 00100 00100 11111 00100 00100 00000",
 '=': "00000 00000 11111 00000 11111 00000 00000", '*': "00000 10101 01110 11111 01110 10101 00000",
 '/': "00001 00001 00010 00100 01000 10000 10000", '#': "01010 01010 11111 01010 11111 01010 01010",
 '@': "01110 10001 10111 10101 10111 10000 01110", '(': "00010 00100 01000 01000 01000 00100 00010",
 ')': "01000 00100 00010 00010 00010 00100 01000", '_': "00000 00000 00000 00000 00000 00000 11111",
 "'": "00100 00100 01000 00000 00000 00000 00000", '&': "01100 10010 10100 01000 10101 10010 01101",
 '%': "11001 11010 00010 00100 01000 01011 10011", '$': "00100 01111 10100 01110 00101 11110 00100",
 '<': "00010 00100 01000 10000 01000 00100 00010", '>': "01000 00100 00010 00001 00010 00100 01000",
}
BITS = {k: [[int(c) for c in row] for row in v.split()] for k, v in GLYPHS.items()}
LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def clean(text):
    """keep only what we can draw: A-Z 0-9 symbols, single spaces"""
    out = "".join(c for c in text.upper() if c in BITS or c == " ")
    return " ".join(out.split())


def width(ch, style):
    """box width of a glyph in units (no margins)"""
    if style == "pixel":
        return 4.0
    return float(STROKES[ch][0]) if ch in STROKES else 4.0


def _gap(style):
    return 1.0 if style == "pixel" else .9


def advance(ch, style):
    """pen movement: the glyph footprint (box + stroke margins) plus a gap"""
    if ch == " ":
        return SPACE_ADV
    if style == "pixel":
        return 6.0
    return width(ch, style) + 2 * RADIUS[style] + _gap(style)


def line_width(line, style):
    return sum(advance(c, style) for c in line) - _gap(style)       # no trailing gap


def split_lines(words, n, style):
    """cut the words into n lines of the most even width (brute force; few words)"""
    best = None

    def rec(start, left, acc):
        nonlocal best
        if left == 1:
            lines = acc + [" ".join(words[start:])]
            cost = max(line_width(l, style) for l in lines)
            if best is None or cost < best[0]:
                best = (cost, lines)
            return
        for cut in range(start + 1, len(words) - left + 2):
            rec(cut, left - 1, acc + [" ".join(words[start:cut])])
    rec(0, n, [])
    return best[1]


def layout(text, W, H, style="normal", max_stretch=1.7):
    """choose how many lines (1-3) give the biggest letters.
    -> (scale, lines, stretch, units_w, units_h): scale = pixels per unit vertically,
    stretch = how much wider a unit is than tall (drawn wide to fill a terminal,
    squeezed when the text is long)"""
    words = text.split() or [" "]
    best = None
    for n in range(1, min(len(words), 3) + 1):
        lines = split_lines(words, n, style)
        uw = max(line_width(l, style) for l in lines)
        uh = n * LINE_H + (n - 1) * LINE_GAP
        s = .9 * H / uh
        stretch = min(max_stretch, max(.6, .9 * W / (uw * s)))
        s = min(s, .9 * W / (uw * stretch))
        score = s * s * stretch
        if best is None or score > best[0] * 1.001:
            best = (score, s, lines, stretch, uw, uh)
    return best[1:]


# ------------------------------------------------------------- rasterizing
_cache = {}


def _segments(points_list, shear, dy):
    segs = []
    for pts in points_list:
        pts = [(x + (3 - y) * shear, y + dy) for x, y in pts]
        if len(pts) == 1 or (len(pts) == 2 and pts[0] == pts[1]):
            segs.append((pts[0], pts[0]))
        else:
            for a, b in zip(pts, pts[1:]):
                segs.append((a, b))
    return segs


def _sdf(segs_px, R, ox, oy):
    """rasterize segments (pixel coords relative to ox, oy) -> (w, h, bx, by, alpha, core)
    alpha = coverage with ~1px soft edge, core = 1 on the stroke's center line, 0 at its edge"""
    pad = R + 1.5
    xs = [p[0] for s in segs_px for p in s]
    ys = [p[1] for s in segs_px for p in s]
    bx0, bx1 = int(math.floor(min(xs) - pad)), int(math.ceil(max(xs) + pad))
    by0, by1 = int(math.floor(min(ys) - pad)), int(math.ceil(max(ys) + pad))
    w, h = bx1 - bx0, by1 - by0
    alpha, core = [0.0] * (w * h), [0.0] * (w * h)
    prep = []
    for (ax, ay), (bx, by) in segs_px:
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        prep.append((ax, ay, dx, dy, 1.0 / l2 if l2 > 1e-9 else 0.0, min(ax, bx), max(ax, bx), min(ay, by), max(ay, by)))
    edge = R + .75
    sqrt = math.sqrt
    for py in range(by0, by1):
        yc = py + .5
        cand = [s for s in prep if s[7] - pad <= yc <= s[8] + pad]
        if not cand:
            continue
        row = (py - by0) * w - bx0
        for px in range(bx0, bx1):
            xc = px + .5
            best = 1e18
            for ax, ay, dx, dy, inv, xmin, xmax, _, _ in cand:
                if xc < xmin - pad or xc > xmax + pad:
                    continue
                t = ((xc - ax) * dx + (yc - ay) * dy) * inv
                t = 0.0 if t < 0 else (1.0 if t > 1 else t)
                ex, ey = xc - ax - dx * t, yc - ay - dy * t
                d2 = ex * ex + ey * ey
                if d2 < best:
                    best = d2
            if best < 1e17:
                d = sqrt(best)
                if d < edge:
                    a = (edge - d) / 1.5
                    alpha[row + px] = 1.0 if a > 1 else a
                    core[row + px] = max(0.0, 1.0 - d / R)
    return w, h, bx0, by0, alpha, core


def build_masks(text, W, H, style="normal"):
    """-> dict(alpha, core, box=(x0,y0,x1,y1)) flat lists of W*H floats for the text"""
    s, lines, stretch, uw, uh = layout(text, W, H, style)
    ux, uy = s * stretch, s
    X0, Y0 = (W - uw * ux) / 2, (H - uh * uy) / 2
    alpha, core = [0.0] * (W * H), [0.0] * (W * H)
    R = RADIUS[style] * s
    shear = .28 if style == "italic" else 0.0
    pixel = style == "pixel"
    pen_idx = 0
    for li, line in enumerate(lines):
        pen = (uw - line_width(line, style)) / 2
        for ch in line:
            adv = advance(ch, style)
            if ch != " ":
                gx, gy = X0 + pen * ux, Y0 + li * (LINE_H + LINE_GAP) * uy
                dy = math.sin(pen_idx * 1.1) * .35 if style == "wavy" else 0.0
                if pixel:
                    _stamp_bitmap(alpha, core, W, H, ch, gx, gy + dy * uy, ux, uy)
                else:
                    _stamp_glyph(alpha, core, W, H, ch, gx, gy + dy * uy, ux, uy, R, shear, style)
            pen += adv
            pen_idx += 1
    xs = [i % W for i, v in enumerate(alpha) if v > .1] or [0]
    ys = [i // W for i, v in enumerate(alpha) if v > .1] or [0]
    return {"alpha": alpha, "core": core, "box": (min(xs), min(ys), max(xs) + 1, max(ys) + 1),
            "R": R if not pixel else max(1.0, ux / 2)}


def _stamp_glyph(alpha, core, W, H, ch, gx, gy, ux, uy, R, shear, style):
    if ch not in STROKES:
        return
    ix, iy = math.floor(gx), math.floor(gy)
    fx, fy = round((gx - ix) * 4) / 4, round((gy - iy) * 4) / 4
    key = (ch, style, round(ux, 2), round(uy, 2), round(R, 2), shear, fx, fy)
    got = _cache.get(key)
    if got is None:
        segs = _segments(STROKES[ch][1], shear, 0.0)
        # glyph origin = (stroke margin .5, .5) inside its footprint
        rm = RADIUS[style]
        segs_px = [(((a[0] + rm) * ux + fx, (a[1] + .5) * uy + fy), ((b[0] + rm) * ux + fx, (b[1] + .5) * uy + fy)) for a, b in segs]
        got = _sdf(segs_px, R, 0, 0)
        if len(_cache) > 600:
            _cache.clear()
        _cache[key] = got
    w, h, bx0, by0, a, c = got
    for y in range(h):
        yy = iy + by0 + y
        if not 0 <= yy < H:
            continue
        for x in range(w):
            v = a[y * w + x]
            if v:
                xx = ix + bx0 + x
                if 0 <= xx < W:
                    i = yy * W + xx
                    if v > alpha[i]:
                        alpha[i] = v
                    cv = c[y * w + x]
                    if cv > core[i]:
                        core[i] = cv


def _stamp_bitmap(alpha, core, W, H, ch, gx, gy, ux, uy):
    rows = BITS[ch]
    for ry in range(7):
        for rx in range(5):
            if rows[ry][rx]:
                x0, x1 = int(round(gx + rx * ux)), int(round(gx + (rx + 1) * ux))
                y0, y1 = int(round(gy + ry * uy)), int(round(gy + (ry + 1) * uy))
                for y in range(max(0, y0), min(H, y1)):
                    for x in range(max(0, x0), min(W, x1)):
                        i = y * W + x
                        alpha[i] = 1.0
                        # bevel-ish core: bright in the middle of every block
                        cx = 1 - abs((x + .5 - (x0 + x1) / 2) / max(1, (x1 - x0) / 2))
                        cy = 1 - abs((y + .5 - (y0 + y1) / 2) / max(1, (y1 - y0) / 2))
                        core[i] = max(core[i], min(cx, cy))
