#!/usr/bin/env python3
"""bigletters - a random letter (or a word, a clock, a countdown) fills the
whole terminal, with colors, effects and animations. Pure Python 3, no
dependencies. Needs a truecolor terminal (most modern ones).

  python3 bigletter.py                 random letter, Space = next one
  python3 bigletter.py --auto          change it by itself
  python3 bigletter.py --word hello    start with a word
  python3 bigletter.py --letters claude    random letters only from c l a u d e
  echo "one two three" | python3 bigletter.py     words from stdin / --file
  python3 bigletter.py --clock         big clock;  --countdown 60  a timer
  python3 bigletter.py --record out.gif    record the show to a GIF

Keys: Space/Enter next   any letter/digit shows it   Esc type your own text
      Tab new effects    Ctrl+L lock effects   Ctrl+T theme   Ctrl+F font
      Ctrl+P pause       + / - speed           ?  help        Ctrl+C quit
Run with --list-effects to see every effect name (usable with --bg, --fill,
--geo, --deco, --intro, --font, --theme).
"""
import argparse, math, os, random, shutil, sys, time

try:
    import select, termios, tty
    POSIX = True
except ImportError:          # Windows
    import msvcrt
    POSIX = False

__version__ = "0.2.0"

# ---------------------------------------------------------------- glyphs
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

# ------------------------------------------------------- effect catalogs
BG_NAMES = ["plasma", "stripes", "rain", "rings", "checkers", "stars", "spiral", "flames", "aurora", "grid"]
FILL_NAMES = ["rainbow", "neon", "plasma", "fire", "bands", "outline", "glitter", "chrome", "spectrum", "strobe"]
GEO_NAMES = ["breathe", "wave", "spin", "glitch", "bounce", "zoom", "shear", "jelly", "orbit", "fly"]
DECO_NAMES = ["none", "extrude", "shadow", "mirror"]
INTRO_NAMES = ["pop", "typewriter", "assemble", "drop"]
FONT_NAMES = ["normal", "bold", "thin", "pixel", "italic", "wavy"]
THEME_NAMES = ["rainbow", "neon", "fire", "ice", "retro", "mono"]
N_BG, N_FILL, N_GEO, N_DECO, N_INTRO = (len(x) for x in (BG_NAMES, FILL_NAMES, GEO_NAMES, DECO_NAMES, INTRO_NAMES))
AXIS_SIZE = {"bg": N_BG, "fill": N_FILL, "geo": N_GEO, "deco": N_DECO, "intro": N_INTRO}
THEMES = {"rainbow": None, "neon": (128, 100), "fire": (0, 43), "ice": (95, 80), "retro": (170, 86), "mono": "mono"}
THEME = None
FPS = 25
EFFECT_SECS = 2.5
AUTO_SECS = 5.0


def hue_table():
    t = []
    for i in range(256):
        h = i / 256 * 6
        f = h - int(h)
        p, q, u = 0, int(255 * (1 - f)), int(255 * f)
        r, g, b = [(255, u, p), (q, 255, p), (p, 255, u), (p, q, 255), (u, p, 255), (255, p, q)][int(h) % 6]
        t.append((r, g, b))
    return t
HUE = hue_table()


def hue(h):
    """a color for position h (any number; the circle is 256 long), shaped by the theme"""
    i = int(h) & 255
    th = THEME
    if th is None:
        return HUE[i]
    tri = 1 - abs(i / 128 - 1)                      # 0..1..0 along the circle
    if th == "mono":
        v = int(60 + 195 * tri)
        return (v // 6, v, v // 3)
    return HUE[int(th[0] + tri * th[1]) & 255]


def set_theme(name):
    global THEME
    THEME = THEMES[name]


def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def blur(src, w, h, r):
    """box blur (rows, then columns) with sliding sums"""
    def line(vals):
        n, out, s = len(vals), [0.0] * len(vals), 0.0
        for i in range(min(r, n)):
            s += vals[i]
        win = 2 * r + 1
        for i in range(n):
            if i + r < n: s += vals[i + r]
            if i - r - 1 >= 0: s -= vals[i - r - 1]
            out[i] = s / win
        return out
    rows = [line(src[y * w:(y + 1) * w]) for y in range(h)]
    cols = [line([rows[y][x] for y in range(h)]) for x in range(w)]
    return [cols[x][y] for y in range(h) for x in range(w)]


def clean(text):
    """keep only what we can draw: A-Z 0-9 symbols, single spaces"""
    out = "".join(c for c in text.upper() if c in BITS or c == " ")
    return " ".join(out.split())


def split_lines(words, n):
    """cut the words into n lines of the most even length (brute force; few words)"""
    best = None

    def rec(start, left, acc):
        nonlocal best
        if left == 1:
            lines = acc + [" ".join(words[start:])]
            cost = max(len(l) for l in lines)
            if best is None or cost < best[0]:
                best = (cost, lines)
            return
        for cut in range(start + 1, len(words) - left + 2):
            rec(cut, left - 1, acc + [" ".join(words[start:cut])])
    rec(0, n, [])
    return best[1]


def layout(text, W, H, max_stretch=1.7):
    """choose how many lines (1-3) give the biggest letters -> (scale, lines, stretch).
    scale = pixels per glyph row; stretch = how much wider than tall a glyph column is
    (letters are drawn wide to fill a terminal, long text is squeezed to fit)"""
    words = text.split() or [" "]
    best = None
    for n in range(1, min(len(words), 3) + 1):
        lines = split_lines(words, n)
        cols = max(len(l) * 6 - 1 for l in lines)
        rows = n * 7 + (n - 1) * 2
        s = .9 * H / rows
        stretch = min(max_stretch, max(.6, .9 * W / (cols * s)))
        s = min(s, .9 * W / (cols * stretch))
        score = s * s * stretch
        if best is None or score > best[0] * 1.001:
            best = (score, s, lines, stretch)
    return best[1], best[2], best[3]


def tri_hash(a, b, c=0):
    return ((a * 73856093) ^ (b * 19349663) ^ (c * 83492791)) & 0xffff


# ------------------------------------------------------------ the show
class Show:
    def __init__(self, w, h, pool=None, text=None, words=None, locks=None, font=0):
        self.w, self.h = w, h * 2                    # pixels: a cell = 2 half-block pixels
        self.pool = pool or list(LETTERS)
        self.words = words or []
        self.wi = -1
        self.text = ""
        self.parts = []                              # sparks
        self.fly = []                                # particles that assemble the letter
        self.flash = 0.0
        self.q = 1                                   # block size (adaptive quality)
        self.locks = dict(locks or {})               # axis -> fixed index
        self.all_locked = False
        self.font = font
        self.born = 0.0
        self.outro_t0 = None
        self.pending = None
        self.mask = self.glow = None
        self.cols_delay = [0.0] * self.w
        self.bg = random.randrange(N_BG)
        self.fill = random.randrange(N_FILL)
        self.geo = random.randrange(N_GEO)
        self.deco = random.choice([0, 0, 1, 2, 3])
        self.intro = random.randrange(N_INTRO)
        self.apply_locks()
        self.set_text(text or self.next_text(), 0.0)

    def apply_locks(self):
        for axis, v in self.locks.items():
            setattr(self, axis, v)

    # ---- text
    def next_text(self):
        if self.words:
            self.wi = (self.wi + 1) % len(self.words)
            return self.words[self.wi]
        opts = [c for c in self.pool if c != self.text] or self.pool
        return random.choice(opts)

    def set_text(self, text, now, quiet=False):
        """show text; quiet = just swap it (clock digits): no intro, no flash"""
        old = self.mask
        self.text = text
        self.build_mask()
        if quiet:
            return
        self.born, self.flash, self.outro_t0, self.pending = now, 0.55, None, None
        if "intro" not in self.locks:
            self.intro = random.randrange(N_INTRO)
        if old is not None and self.intro == 2:
            self.scatter(old, 70)                    # the old letter crumbles...
        else:
            self.burst(self.w / 2, self.h / 2, 60)
        self.cols_delay = [random.random() * .6 for _ in range(self.w)]
        self.fly = []
        if self.intro == 2:
            self.make_fly()                          # ...and the new one is assembled

    def change(self, text, now):
        """switch text; the typewriter intro erases the old one first"""
        if text is None:
            return
        if self.intro == 1 and self.outro_t0 is None and now - self.born > .5:
            self.outro_t0, self.pending = now, text
        else:
            self.set_text(text, now)

    # ---- mask
    def build_mask(self):
        W, H = self.w, self.h
        s, lines, stretch = layout(self.text, W, H)
        n = len(lines)
        cols = max(len(l) * 6 - 1 for l in lines)
        rows = n * 7 + (n - 1) * 2
        g = [[0] * cols for _ in range(rows)]
        for li, line in enumerate(lines):
            start = (cols - (len(line) * 6 - 1)) // 2
            for k, ch in enumerate(line):
                if ch in BITS:
                    for y in range(7):
                        g[li * 9 + y][start + k * 6:start + k * 6 + 5] = BITS[ch][y]
        bw, bh = cols * s * stretch, rows * s
        x0, y0 = (W - bw) / 2, (H - bh) / 2
        self.bx0, self.bx1, self.by0, self.by1 = x0, x0 + bw, y0, y0 + bh
        style = FONT_NAMES[self.font]
        lo, hi = {"bold": (.1, .4), "thin": (.62, .9)}.get(style, (.3, .7))

        def px(ix, iy):
            return g[iy][ix] if 0 <= ix < cols and 0 <= iy < rows else 0
        wob = max(1.0, s * .35)
        m = []
        for y in range(H):
            for x in range(W):
                xs, ys = x, y
                if style == "italic":
                    xs = x - (H / 2 - y) * .28
                elif style == "wavy":
                    ys = y + math.sin(x * .25) * wob
                fy = (ys - y0) / bh * rows - 0.5
                fx = (xs - x0) / bw * cols - 0.5
                if style == "pixel":
                    m.append(float(px(math.floor(fx + .5), math.floor(fy + .5))))
                    continue
                ix, iy = math.floor(fx), math.floor(fy)
                wx, wy = fx - ix, fy - iy
                v = (px(ix, iy) * (1 - wx) + px(ix + 1, iy) * wx) * (1 - wy) + \
                    (px(ix, iy + 1) * (1 - wx) + px(ix + 1, iy + 1) * wx) * wy
                m.append(smooth(lo, hi, v))
        self.mask = m
        self.glow = [min(1.0, v * 2.2) for v in blur(m, W, H, max(2, W // 45))]

    def on_letter(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h and self.mask[y * self.w + x] > .7

    def random_letter_point(self):
        for _ in range(40):
            x, y = random.randrange(self.w), random.randrange(self.h)
            if self.on_letter(x, y):
                return x, y
        return self.w // 2, self.h // 2

    # ---- particles
    def burst(self, x, y, n):
        for _ in range(n):
            a, s = random.random() * 6.283, random.uniform(8, 40)
            self.parts.append([x, y, math.cos(a) * s, math.sin(a) * s * 0.6 - 6, random.uniform(0.7, 1.6), random.randrange(256)])

    def scatter(self, mask, n):
        """fly apart from the pixels of the old letter"""
        W = self.w
        for _ in range(n):
            x, y = W // 2, self.h // 2
            for _ in range(30):
                cx, cy = random.randrange(W), random.randrange(self.h)
                if mask[cy * W + cx] > .7:
                    x, y = cx, cy
                    break
            self.parts.append([x, y, (x - W / 2) * .8 + random.uniform(-6, 6), (y - self.h / 2) * .8 + random.uniform(-6, 6) - 4,
                               random.uniform(.7, 1.5), random.randrange(256)])

    def make_fly(self):
        for _ in range(min(260, max(60, self.w * self.h // 40))):
            tx, ty = self.random_letter_point()
            edge = random.randrange(4)
            sx = random.randrange(self.w) if edge < 2 else (0 if edge == 2 else self.w - 1)
            sy = (0 if edge == 0 else self.h - 1) if edge < 2 else random.randrange(self.h)
            self.fly.append((sx, sy, tx, ty, random.randrange(256)))

    def new_effects(self, force=False):
        """pick fresh effects for every axis that is not locked"""
        if self.all_locked and not force:
            return
        for axis, n in AXIS_SIZE.items():
            if axis in self.locks or axis == "intro":
                continue
            cur = getattr(self, axis)
            if axis == "deco":
                setattr(self, axis, random.choices(range(n), [4, 2, 2, 2])[0])
            else:
                setattr(self, axis, (cur + random.randrange(1, n)) % n)

    # ---- colors
    def bgc(self, x, y, t):
        m = self.bg
        if m == 0:                                  # plasma
            s = math.sin(x * .11 + t) + math.sin(y * .09 + t * 1.3) + math.sin((x + y) * .06 + t * .7) + math.sin((x - y) * .05 - t)
            r, g, b = hue(s * 20 + t * 30)
            f = .22 + .1 * s
        elif m == 1:                                # stripes
            r, g, b = hue((x + y) * 3 + t * 60)
            f = .22 + .12 * math.sin((x - y) * .15 - t * 2)
        elif m == 2:                                # digital rain
            cx = x // 2
            hc = (cx * 2654435761) & 0xffff
            head = (t * (8 + hc % 12) + hc) % (self.h + 20)
            d = head - y
            if 0 <= d < 14 and ((x * 7 + y * 13 + int(t * 6) * (hc | 1)) & 3):
                v = 1 - d / 14
                return (int(180 * v * (d < 1)), int(255 * v), int(90 * v))
            return (0, 8, 4)
        elif m == 3:                                # rings
            d = math.hypot(x - self.w / 2, y - self.h / 2)
            r, g, b = hue(d * 5 - t * 90)
            f = .2 + .12 * math.sin(d * .4 - t * 3)
        elif m == 4:                                # checkers + wave
            cx = int((x + math.sin(y * .3 + t * 2) * 2) // 4)
            cy = int((y + math.sin(x * .2 + t * 2) * 2) // 4)
            r, g, b = hue(t * 40 + ((cx + cy) & 1) * 120)
            f = .3 if (cx + cy) & 1 else .12
        elif m == 5:                                # starfield, 3 parallax layers
            for layer, sp in ((0, 6), (1, 14), (2, 30)):
                if tri_hash(x + int(t * sp), y, layer) < 110:
                    v = 90 + layer * 80
                    return (v, v, min(255, v + 30))
            return (0, 0, 12 + int(6 * math.sin(y * .1 + t)))
        elif m == 6:                                # spiral
            dx, dy = x - self.w / 2, y - self.h / 2
            ang, d = math.atan2(dy, dx), math.hypot(dx, dy)
            r, g, b = hue(ang * 128 / math.pi * 3 + d * 4 - t * 90)
            f = .22 + .12 * math.sin(d * .3 - ang * 3 + t * 4)
        elif m == 7:                                # flames from the bottom
            yy = (self.h - y) / self.h
            n = math.sin(x * .3 + t * 8) + math.sin(x * .17 - t * 6) * .7 + math.sin(x * .5 + y * .2 + t * 10) * .3
            v = max(0.0, 1.05 - yy * 1.6 + n * .16)
            return (int(min(255, v * 480) * .6), int(min(255, max(0, v - .3) * 480) * .6), int(min(255, max(0, v - .85) * 400) * .6))
        elif m == 8:                                # aurora ribbons
            r = g = b = 0.0
            for k, base in enumerate((.32, .5, .66)):
                y0 = self.h * base + math.sin(x * .05 + t * (.7 + k * .3) + k * 2) * self.h * .1
                v = 1 / (1 + ((y - y0) / (self.h * .06)) ** 2)
                cr, cg, cb = hue(90 + k * 70 + x * .4 + t * 15)
                r, g, b = r + cr * v, g + cg * v, b + cb * v
            return (min(255, int(r * .6)), min(255, int(g * .6)), min(255, int(b * .6) + 12))
        else:                                       # synthwave grid
            hz = self.h * .5
            if y <= hz:
                k = y / hz
                return (int(20 + 150 * k * k), int(10 + 20 * k), int(50 + 60 * k))
            zz = hz / max(y - hz, .5)
            line = ((zz * 1.5 - t * 3) % 1) < .12 or ((((x - self.w / 2) / self.w) * zz * 8) % 1) < .07
            k = min(1.0, (y - hz) / (self.h * .25))
            if line:
                return (int(255 * k), int(40 * k), int(200 * k))
            return (12, 0, 30)
        f = max(0.0, f)
        return (int(r * f), int(g * f), int(b * f))

    def fillc(self, x, y, t):
        m = self.fill
        if m == 0:
            return hue((x + y) * 2 + t * 70)
        if m == 1:
            r, g, b = hue(t * 40)
            f = .8 + .2 * math.sin(t * 5)
            if ((y + int(t * 20)) >> 1) & 1:
                f *= .7
            return (int(r * f), int(g * f), int(b * f))
        if m == 2:
            s = math.sin(x * .2 + t * 2) + math.sin(y * .3 - t * 3) + math.sin((x + y) * .1 + t)
            return hue(s * 40 + t * 80)
        if m == 3:
            s = math.sin(y * .4 - t * 6) + math.sin(x * .1 + t * 2) * .5
            r, g, b = hue(8 + (s + 1.5) * 14)
            if THEME is None:
                return (min(255, r + 30), min(255, g + 20), b)
            return (r, g, b)
        if m == 4:                                  # two-color bands
            st = ((x + y) // 6 + int(t * 4)) & 1
            return hue(t * 30 + st * 128)
        if m == 5:                                  # outline: bright edge
            return hue(t * 60 + y * 2)
        if m == 6:                                  # rainbow with glitter
            if tri_hash(x, y, int(t * 12)) % 30 == 0:
                return (255, 255, 255)
            return hue((x + y) * 2 + t * 70)
        if m == 7:                                  # chrome
            b_ = .5 + .5 * math.sin(y * .5 + t * 2 + x * .05)
            if b_ > .92:
                return (255, 255, 255)
            return (int(b_ * 200 + 30), int(b_ * 215 + 40), int(b_ * 235 + 20))
        if m == 8:                                  # rainbow across the width
            return hue(x * 512 / self.w + t * 50)
        st = ((y // 6) + int(t * 8)) & 1            # strobe
        return hue(t * 30 + st * 128)

    # ---- frame
    def frame(self, t):
        """-> grid of rows of (top, bottom) colors, one entry per terminal cell"""
        W, H = self.w, self.h
        age = t - self.born
        geo, deco, intro = self.geo, self.deco, self.intro
        scale = 1.0
        if intro == 0 and age < .55:
            x = age / .55 - 1
            scale = max(.02, 1 + 2.70158 * x ** 3 + 1.70158 * x * x)
        scale *= 1 + .05 * math.sin(t * 3)
        cx, cy = W / 2, H / 2
        offx = offy = 0.0
        alpha_mul = 1.0
        rowoff = [0.0] * H
        rot = None
        if geo == 1:                                 # wave
            rowoff = [math.sin(y * .35 + t * 5) * W * .035 for y in range(H)]
        elif geo == 2:                               # spin around the vertical axis
            rot = math.cos(t * 1.1)
        elif geo == 3:                               # glitch
            offy = math.sin(t * 2.3) * H * .06
            if (int(t * 8) // 5) % 3 != 0:
                gt = int(t * 8)
                for y in range(H):
                    hh = tri_hash(y // 4, gt)
                    if hh % 4 == 0:
                        rowoff[y] = (hh % 17 - 8) * W / 90
        elif geo == 4:                               # bounce
            offy = H * .06 - abs(math.sin(t * 3)) * H * .14
        elif geo == 5:                               # big zoom pulse
            scale *= .78 + .27 * math.sin(t * 2.2)
        elif geo == 6:                               # shear
            sh = math.sin(t * 2) * .5
            rowoff = [(y - cy) * sh for y in range(H)]
        elif geo == 8:                               # orbit
            offx, offy = math.cos(t * 1.7) * W * .07, math.sin(t * 1.7) * H * .07
        elif geo == 9:                               # fly in from the distance, again and again
            ph = (t * .35) % 1
            scale *= .04 + 1.12 * ph ** 2
            alpha_mul = 1 - smooth(.85, 1.0, ph)
        ym = H * .66
        if deco == 3:                                # mirror: smaller letter above a water line
            scale *= .62
            offy -= H * .13
        scale = max(scale, .02)
        sx = sy = 1 / scale
        if rot is not None:
            sx = 1 / (scale * max(abs(rot), .06)) * (1 if rot >= 0 else -1)
        if geo == 7:                                 # jelly
            j = .2 * math.sin(t * 5)
            sx, sy = sx / (1 + j), sy / (1 - j)
        mask, glow = self.mask, self.glow
        fl = self.flash
        fill5 = self.fill == 5

        # intro visibility
        type_p = None
        if self.outro_t0 is not None:
            type_p = max(0.0, 1 - (t - self.outro_t0) / .45)
        elif intro == 1 and age < .25 + .12 * len(self.text):
            type_p = age / (.25 + .12 * len(self.text))
        revx = self.bx0 + (type_p if type_p is not None else 1) * (self.bx1 - self.bx0)
        asm = smooth(.9, 1.5, age) if intro == 2 and age < 1.5 else 1.0
        dropping = intro == 3 and age < 1.3
        delays = self.cols_delay
        ex_a = t * .9
        ex_dx, ex_dy = math.cos(ex_a), math.sin(ex_a) * .6
        q = self.q

        def sample(x, y):
            """(mask, glow) of the letter at screen pixel (x, y)"""
            v = int((y - cy - offy) * sy + cy)
            u = int((x - cx - offx) * sx + cx + rowoff[y])
            if 0 <= u < W and 0 <= v < H:
                i = v * W + u
                return mask[i], glow[i]
            return 0.0, 0.0

        pix = [[None] * W for _ in range(H)]
        for y0 in range(0, H, q):
            for x0 in range(0, W, q):
                x, y = min(x0 + q // 2, W - 1), min(y0 + q // 2, H - 1)
                refl = deco == 3 and y > ym
                ysrc = 2 * ym - y + math.sin(y * .6 + t * 4) * 1.2 if refl else y
                ysrc = min(max(int(ysrc), 0), H - 1)
                m, g = sample(x, ysrc)
                vis = alpha_mul * asm
                head = False
                if type_p is not None and x > revx:
                    vis = 0.0
                elif dropping:
                    front = (age - delays[x]) * H * 1.8
                    if ysrc > front:
                        vis = 0.0
                    elif front - ysrc < 3:
                        head = True
                m, g = m * vis, g * vis
                if refl:
                    m, g = m * .35, g * .3
                r, gg, b = self.bgc(x, y, t)
                if deco == 3 and y > ym:
                    r, gg, b = int(r * .7), int(gg * .75), int(b * .9) + 10
                elif deco == 3 and abs(y - ym) < 1:
                    r, gg, b = 150, 200, 255
                if deco in (1, 2) and m < .5 and g > .04:      # 3D side / long shadow
                    steps = 6 if deco == 1 else 10
                    reach = H * (.05 if deco == 1 else .15)
                    dx, dy = (ex_dx, ex_dy) if deco == 1 else (.7, .7)
                    for k in range(1, steps + 1):
                        d = reach * k / steps
                        sm, _ = sample(int(x - dx * d), min(max(int(y - dy * d), 0), H - 1))
                        if sm * vis > .5:
                            if deco == 1:
                                fr, fg, fb = self.fillc(x, y, t)
                                f = .3 + .35 * (1 - k / steps)
                                r, gg, b = int(fr * f), int(fg * f), int(fb * f)
                                m, g = 1.0, 0.0
                            else:
                                f = .3 + .5 * k / steps
                                r, gg, b = int(r * f), int(gg * f), int(b * f)
                            break
                if g > .01:
                    gr, ggg, gb = hue(t * 40 + 40)
                    k = g * (1 - m) * .8
                    r, gg, b = r + gr * k, gg + ggg * k, b + gb * k
                if fill5:
                    m = max(0.0, 1 - abs(m - .5) * 2.4)
                if m > .01:
                    fr, fg, fb = self.fillc(x, y, t)
                    if refl:
                        fr, fg, fb = fr * .8, fg * .85, fb
                    r, gg, b = r + (fr - r) * m, gg + (fg - gg) * m, b + (fb - b) * m
                    if deco == 1 and m > .5:                     # rim light on the front face
                        sm, _ = sample(x + 2, min(y + 2, H - 1))
                        if sm < .4:
                            r, gg, b = r + 70, gg + 70, b + 70
                    if head:
                        r, gg, b = 210, 255, 220
                if type_p is not None and self.by0 <= y <= self.by1 and 0 < x - revx < 2 and (type_p < 1 or int(t * 2) % 2 == 0):
                    r, gg, b = 255, 255, 255             # typewriter cursor
                if fl > 0:
                    r, gg, b = r + 255 * fl, gg + 255 * fl, b + 255 * fl
                c = (max(0, min(255, int(r))), max(0, min(255, int(gg))), max(0, min(255, int(b))))
                for yy in range(y0, min(y0 + q, H)):
                    row = pix[yy]
                    for xx in range(x0, min(x0 + q, W)):
                        row[xx] = c
        if self.fly and age < 1.4:                   # particles flying into the letter
            p = min(1.0, age / 1.2)
            e = 1 - (1 - p) ** 3
            for sx_, sy_, tx, ty, hh in self.fly:
                x, y = int(sx_ + (tx - sx_) * e), int(sy_ + (ty - sy_) * e)
                c = (255, 255, 255) if int(t * 10 + hh) % 3 == 0 else hue(hh + t * 60)
                for yy in (y, y + 1):
                    for xx in (x, x + 1):
                        if 0 <= xx < W and 0 <= yy < H:
                            pix[yy][xx] = c
        for p in self.parts:                         # sparks
            x, y = int(p[0]), int(p[1])
            if 0 <= x < W and 0 <= y < H:
                pix[y][x] = (255, 255, 255) if int(t * 10 + p[5]) % 4 == 0 else hue(p[5] + t * 60)
        return [[(pix[y][x], pix[y + 1][x]) for x in range(W)] for y in range(0, H, 2)]

    def step(self, dt, t):
        self.flash = max(0.0, self.flash - dt * 2.5)
        for p in self.parts:
            p[0] += p[2] * dt; p[1] += p[3] * dt; p[3] += 25 * dt; p[4] -= dt
        self.parts = [p for p in self.parts if p[4] > 0]
        if self.outro_t0 is not None and t - self.outro_t0 >= .45:
            text = self.pending
            self.outro_t0 = self.pending = None
            self.set_text(text, t)
        if self.pending is None and dt > 0:
            for _ in range(2):                       # sparks fall off the letter
                if len(self.parts) < 300:
                    x, y = random.randrange(self.w), random.randrange(self.h)
                    if self.on_letter(x, y):
                        self.parts.append([x, y, random.uniform(-6, 6), random.uniform(-14, -2), random.uniform(.4, 1), random.randrange(256)])


# ------------------------------------------------------------- GIF writer
def lzw_encode(data, min_bits=8):
    """GIF flavour of LZW: bytes of palette indices -> compressed bytes"""
    clear, eoi = 1 << min_bits, (1 << min_bits) + 1
    out, cur, nbits = bytearray(), 0, 0
    code_size, next_code, table = min_bits + 1, eoi + 1, {}

    def emit(code):
        nonlocal cur, nbits
        cur |= code << nbits
        nbits += code_size
        while nbits >= 8:
            out.append(cur & 255)
            cur >>= 8
            nbits -= 8

    emit(clear)
    if data:
        prefix = data[0]
        for b in data[1:]:
            key = (prefix << 8) | b
            c = table.get(key)
            if c is not None:
                prefix = c
                continue
            emit(prefix)
            if next_code < 4096:
                table[key] = next_code
                if next_code == (1 << code_size) and code_size < 12:
                    code_size += 1
                next_code += 1
            else:
                emit(clear)
                table.clear()
                code_size, next_code = min_bits + 1, eoi + 1
            prefix = b
        emit(prefix)
    emit(eoi)
    if nbits:
        out.append(cur & 255)
    return bytes(out)


def gif_palette():
    pal = bytearray()
    for r in range(6):
        for g in range(6):
            for b in range(6):
                pal += bytes((r * 51, g * 51, b * 51))
    for i in range(40):
        v = int(i * 255 / 39)
        pal += bytes((v, v, v))
    return bytes(pal)


def write_gif(path, frames, w, h, delay_cs):
    """frames: list of bytes (w*h palette indices)"""
    out = bytearray(b"GIF89a" + w.to_bytes(2, "little") + h.to_bytes(2, "little") + bytes((0xF7, 0, 0)))
    out += gif_palette()
    out += b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"
    for fr in frames:
        out += b"\x21\xf9\x04\x00" + delay_cs.to_bytes(2, "little") + b"\x00\x00"
        out += b"\x2c\x00\x00\x00\x00" + w.to_bytes(2, "little") + h.to_bytes(2, "little") + b"\x00\x08"
        data = lzw_encode(fr)
        for i in range(0, len(data), 255):
            chunk = data[i:i + 255]
            out += bytes((len(chunk),)) + chunk
        out += b"\x00"
    out += b"\x3b"
    with open(path, "wb") as f:
        f.write(out)


class Recorder:
    SCALE = 2

    def __init__(self, path, seconds):
        self.path, self.seconds = path, seconds
        self.frames, self.size, self.cache, self.skip = [], None, {}, 0
        self.done = False

    def idx(self, c):
        v = self.cache.get(c)
        if v is None:
            v = 36 * ((c[0] * 5 + 127) // 255) + 6 * ((c[1] * 5 + 127) // 255) + (c[2] * 5 + 127) // 255
            self.cache[c] = v
        return v

    def add(self, grid, t):
        if self.done:
            return
        if t > self.seconds:
            self.done = True
            return
        self.skip ^= 1
        if self.skip:                                # every second frame: ~12 fps is plenty
            return
        S = self.SCALE
        buf = bytearray()
        for row in grid:
            top, bot = bytearray(), bytearray()
            for a, b in row:
                top += bytes((self.idx(a),)) * S
                bot += bytes((self.idx(b),)) * S
            buf += bytes(top) * S + bytes(bot) * S
        self.size = (len(grid[0]) * S, len(grid) * 2 * S)
        self.frames.append(bytes(buf))

    def save(self):
        if not self.frames:
            return None
        write_gif(self.path, self.frames, self.size[0], self.size[1], 8)
        return self.path


# --------------------------------------------------------------- terminal
def paint(grid, status=None):
    buf = []
    for ry, line in enumerate(grid):
        buf.append("\x1b[%d;1H" % (ry + 1))
        last = None
        for top, bot in line:
            if (top, bot) != last:
                buf.append("\x1b[38;2;%d;%d;%d;48;2;%d;%d;%dm" % (top + bot))
                last = (top, bot)
            buf.append("▀")
    if status:
        cols = len(grid[0]) if grid else 0
        buf.append("\x1b[%d;1H\x1b[0;30;47m%s\x1b[0m" % (len(grid), status[:cols].ljust(cols)))
    buf.append("\x1b[0m")
    sys.stdout.write("".join(buf))
    sys.stdout.flush()


def read_keys(fd):
    keys = []
    if POSIX:
        while select.select([fd], [], [], 0)[0]:
            ch = os.read(fd, 64).decode(errors="ignore")
            if not ch:
                break
            if ch == "\x1b":
                keys.append("ESC")
            elif ch.startswith("\x1b"):
                pass                                  # arrow keys etc. - ignore
            else:
                keys.extend(ch)
    else:
        while msvcrt.kbhit():
            c = msvcrt.getwch()
            keys.append("ESC" if c == "\x1b" else c)
    return keys


def resolve(names, value, what):
    """--bg 3 / --bg plasma / --bg random -> index or None"""
    if value is None or value == "random":
        return None
    if value.isdigit() and int(value) < len(names):
        return int(value)
    if value in names:
        return names.index(value)
    sys.exit("bigletter: unknown %s '%s' (try --list-effects)" % (what, value))


def build_parser():
    ap = argparse.ArgumentParser(prog="bigletters", description="A random letter (or word, clock, countdown) fills the whole terminal.")
    ap.add_argument("--letters", metavar="LETTERS", help="pick random letters only from these (e.g. --letters claude)")
    ap.add_argument("--word", metavar="TEXT", help="start by showing this word or phrase")
    ap.add_argument("--file", metavar="PATH", help="show the words of this file one by one ('-' = stdin; piped stdin works too)")
    ap.add_argument("--auto", nargs="?", type=float, const=AUTO_SECS, metavar="SECONDS", help="change the text by itself (default every 5 s)")
    ap.add_argument("--theme", metavar="NAME", help="color theme: " + ", ".join(THEME_NAMES) + ", random")
    for axis in AXIS_SIZE:
        ap.add_argument("--" + axis, metavar="NAME", help="lock the %s effect (name or number, see --list-effects)" % axis)
    ap.add_argument("--font", metavar="NAME", help="letter style: " + ", ".join(FONT_NAMES) + ", random")
    ap.add_argument("--speed", type=float, default=1.0, metavar="X", help="animation speed (default 1)")
    ap.add_argument("--clock", action="store_true", help="show the time as a big clock")
    ap.add_argument("--countdown", type=float, metavar="SECONDS", help="count down from N seconds, then fireworks")
    ap.add_argument("--screensaver", action="store_true", help="auto mode, any key quits")
    ap.add_argument("--record", metavar="FILE.gif", help="record the show to an animated GIF")
    ap.add_argument("--record-seconds", type=float, default=6.0, metavar="N", help="how long to record (default 6)")
    ap.add_argument("--bell", action="store_true", help="beep when the text changes")
    ap.add_argument("--time", type=float, metavar="SECONDS", help="quit after N seconds")
    ap.add_argument("--list-effects", action="store_true", help="print all effect names and exit")
    ap.add_argument("--version", action="version", version="bigletters " + __version__)
    return ap


def fmt_clock():
    return time.strftime("%H:%M:%S")


def fmt_countdown(left):
    left = max(0, int(math.ceil(left)))
    if left >= 3600:
        return "%d:%02d:%02d" % (left // 3600, left // 60 % 60, left % 60)
    return "%02d:%02d" % (left // 60, left % 60)


HELP = " Space next | Esc type text | Tab effects | ^L lock | ^T theme | ^F font | ^P pause | +/- speed | ^C quit "


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.list_effects:
        for label, names in (("bg", BG_NAMES), ("fill", FILL_NAMES), ("geo", GEO_NAMES), ("deco", DECO_NAMES),
                             ("intro", INTRO_NAMES), ("font", FONT_NAMES), ("theme", THEME_NAMES)):
            print("%-6s %s" % (label, ", ".join("%d=%s" % (i, n) for i, n in enumerate(names))))
        return

    locks = {}
    for axis, count in AXIS_SIZE.items():
        names = {"bg": BG_NAMES, "fill": FILL_NAMES, "geo": GEO_NAMES, "deco": DECO_NAMES, "intro": INTRO_NAMES}[axis]
        v = resolve(names, getattr(args, axis), axis)
        if v is not None:
            locks[axis] = v
    font_random = args.font == "random"
    font_i = resolve(FONT_NAMES, args.font, "font") or 0
    theme = args.theme or "rainbow"
    if theme == "random":
        theme = random.choice(THEME_NAMES)
    if theme not in THEMES:
        sys.exit("bigletter: unknown theme '%s' (try --list-effects)" % theme)
    set_theme(theme)

    clock_mode = args.clock or args.countdown is not None
    pool = sorted(set(clean(args.letters or "")) - {" "}) or None
    first = clean(args.word or "") or None
    words = []
    if args.file or (not sys.stdin.isatty() and not clock_mode):
        src = args.file or "-"
        raw = sys.stdin.read() if src == "-" else open(src, encoding="utf-8", errors="ignore").read()
        words = [w for w in (clean(x) for x in raw.split()) if w]
        if not words:
            sys.exit("bigletter: no words to show")
    if not sys.stdout.isatty():
        sys.exit("bigletter: run it in a real terminal")
    keyfd = None
    if POSIX:
        keyfd = sys.stdin.fileno() if sys.stdin.isatty() else os.open("/dev/tty", os.O_RDONLY)
    auto = args.auto
    if args.screensaver and auto is None:
        auto = AUTO_SECS
    if clock_mode:
        auto = None
    old = termios.tcgetattr(keyfd) if POSIX else None
    if POSIX:
        tty.setcbreak(keyfd)
    recorder = Recorder(args.record, args.record_seconds) if args.record else None
    sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[2J")
    try:
        size = shutil.get_terminal_size()
        theme_i = THEME_NAMES.index(theme)
        speed = max(.1, min(8.0, args.speed))
        if font_random:
            font_i = random.randrange(len(FONT_NAMES))
        show = Show(size.columns, size.lines, pool, first, words, locks, font_i)
        clock = 0.0                                  # effective time: speed and pause apply
        paused = False
        last_wall = time.time()
        next_fx, next_auto = EFFECT_SECS, auto
        prompt = None                                # text being typed after Esc, or None
        help_until = 0.0
        msg, msg_until = "", 0.0
        cd_done = None
        last_burst = 0
        frame_s = 1 / FPS

        def note(text):
            nonlocal msg, msg_until
            msg, msg_until = " " + text + " ", clock + 2.0

        def advance():
            """next text for Space / auto"""
            if args.bell:
                sys.stdout.write("\a")
            return show.next_text()

        if clock_mode:
            show.set_text(fmt_clock() if args.clock else fmt_countdown(args.countdown), 0.0)
        if recorder:
            note("recording %s for %gs" % (args.record, args.record_seconds))
        while True:
            wall = time.time()
            dt = min(wall - last_wall, .1)
            last_wall = wall
            if args.time and clock > args.time:
                break
            if not paused:
                clock += dt * speed
            t = clock
            cur = shutil.get_terminal_size()
            if cur != size:
                size = cur
                show = Show(size.columns, size.lines, pool, show.text, words, locks, show.font)
                sys.stdout.write("\x1b[2J")
            for k in read_keys(keyfd):
                if k == "\x03" or (args.screensaver and prompt is None):
                    return
                if prompt is not None:                # typing a letter / word
                    if k == "ESC":
                        prompt = None
                    elif k in ("\r", "\n"):
                        word = clean(prompt)
                        if word and not clock_mode:
                            show.change(word, t)
                            next_auto = t + auto if auto else None
                        prompt = None
                    elif k in ("\x7f", "\b"):
                        prompt = prompt[:-1]
                    elif (k.upper() in BITS or k == " ") and len(prompt) < 40:
                        prompt += k.upper()
                    continue
                if k == "ESC":
                    prompt = ""
                elif k == "\t":
                    show.new_effects(); next_fx = t + EFFECT_SECS
                elif k == "\x10":
                    paused = not paused; note("paused" if paused else "resumed")
                elif k == "\x0c":
                    show.all_locked = not show.all_locked
                    note("effects locked" if show.all_locked else "effects unlocked")
                elif k == "\x14":
                    theme_i = (theme_i + 1) % len(THEME_NAMES); set_theme(THEME_NAMES[theme_i]); note("theme: " + THEME_NAMES[theme_i])
                elif k == "\x06":
                    show.font = (show.font + 1) % len(FONT_NAMES); show.build_mask(); note("font: " + FONT_NAMES[show.font])
                elif k in ("+", "="):
                    speed = min(8.0, speed * 1.25); note("speed x%.2g" % speed)
                elif k in ("-", "_"):
                    speed = max(.1, speed / 1.25); note("speed x%.2g" % speed)
                elif k == "?":
                    help_until = t + 6 if help_until <= t else 0
                elif clock_mode:
                    pass
                elif k.upper() in BITS:
                    show.change(k.upper(), t)
                    next_auto = t + auto if auto else None
                elif k in (" ", "\r", "\n"):
                    show.change(advance(), t)
                    next_auto = t + auto if auto else None
            if clock_mode:                           # new text once a second; fireworks at zero
                if args.clock:
                    text = fmt_clock()
                else:
                    left = args.countdown - clock
                    text = fmt_countdown(left) if left > 0 else "GO!"
                if text != show.text:
                    show.set_text(text, t, quiet=(text != "GO!"))
                    if text == "GO!":
                        cd_done = t
                if cd_done is not None and t - cd_done < 3 and int((t - cd_done) * 3) != last_burst:
                    last_burst = int((t - cd_done) * 3)
                    show.burst(random.uniform(.15, .85) * show.w, random.uniform(.15, .6) * show.h, 70)
            elif auto and next_auto is not None and t >= next_auto:
                show.new_effects()
                if font_random:
                    show.font = random.randrange(len(FONT_NAMES))
                    show.build_mask()
                show.change(advance(), t)
                next_auto, next_fx = t + auto, t + EFFECT_SECS
            elif t >= next_fx:
                show.new_effects(); next_fx = t + EFFECT_SECS
            show.step(0.0 if paused else dt * speed, t)
            t0 = time.time()
            grid = show.frame(t)
            if recorder:
                recorder.add(grid, t)
            status = None
            if prompt is not None:
                status = " Type a letter or word, Enter = show, Esc = cancel:  %s_" % prompt
            elif t < help_until:
                status = HELP
            elif t < msg_until:
                status = msg
            paint(grid, status)
            # adaptive quality: bigger blocks when the terminal is too big for this machine
            spent = time.time() - t0
            if spent > frame_s * 1.6 and show.q < 4:
                show.q += 1
            elif spent < frame_s * .45 and show.q > 1:
                show.q -= 1
            time.sleep(max(0, frame_s - (time.time() - wall)))
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
        if POSIX:
            termios.tcsetattr(keyfd, termios.TCSADRAIN, old)
        if recorder:
            saved = recorder.save()
            print("saved %s (%d frames)" % (saved, len(recorder.frames)) if saved else "nothing recorded")


if __name__ == "__main__":
    main()
