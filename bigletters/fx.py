"""Effects: names, color themes, and the per-pixel background / fill colors."""
import math

BG_NAMES = ["plasma", "stripes", "rain", "rings", "checkers", "stars", "spiral", "flames", "aurora", "grid"]
FILL_NAMES = ["rainbow", "neon", "plasma", "fire", "bands", "outline", "glitter", "chrome", "spectrum", "strobe"]
GEO_NAMES = ["breathe", "wave", "spin", "glitch", "bounce", "zoom", "shear", "jelly", "orbit", "fly"]
DECO_NAMES = ["none", "extrude", "shadow", "mirror"]
INTRO_NAMES = ["pop", "typewriter", "assemble", "drop"]
THEME_NAMES = ["rainbow", "neon", "fire", "ice", "retro", "mono", "gold", "sunset"]
N_BG, N_FILL, N_GEO, N_DECO, N_INTRO = (len(x) for x in (BG_NAMES, FILL_NAMES, GEO_NAMES, DECO_NAMES, INTRO_NAMES))
AXIS_NAMES = {"bg": BG_NAMES, "fill": FILL_NAMES, "geo": GEO_NAMES, "deco": DECO_NAMES, "intro": INTRO_NAMES}
AXIS_SIZE = {k: len(v) for k, v in AXIS_NAMES.items()}

# theme = (start of the hue range, length of the range) on a 256 long hue circle, or "mono"
THEMES = {"rainbow": None, "neon": (128, 100), "fire": (0, 43), "ice": (95, 80), "retro": (170, 86),
          "mono": "mono", "gold": (14, 34), "sunset": (205, 75)}
THEME = None


def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def _hue_table():
    t = []
    for i in range(256):
        h = i / 256 * 6
        f = h - int(h)
        p, q, u = 0, int(255 * (1 - f)), int(255 * f)
        t.append([(255, u, p), (q, 255, p), (p, 255, u), (p, q, 255), (u, p, 255), (255, p, q)][int(h) % 6])
    return t
HUE = _hue_table()


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


def tri_hash(a, b, c=0):
    return ((a * 73856093) ^ (b * 19349663) ^ (c * 83492791)) & 0xffff


def bg_color(sh, m, x, y, t):
    """background color at pixel (x, y); sh gives the size and cached polar maps"""
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
        head = (t * (8 + hc % 12) + hc) % (sh.h + 20)
        d = head - y
        if 0 <= d < 14 and ((x * 7 + y * 13 + int(t * 6) * (hc | 1)) & 3):
            v = 1 - d / 14
            return (int(180 * v * (d < 1)), int(255 * v), int(90 * v))
        return (0, 8, 4)
    elif m == 3:                                # rings
        d = sh.polar()[0][y * sh.w + x]
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
        dist, ang = sh.polar()
        i = y * sh.w + x
        d, a = dist[i], ang[i]
        r, g, b = hue(a * 128 / math.pi * 3 + d * 4 - t * 90)
        f = .22 + .12 * math.sin(d * .3 - a * 3 + t * 4)
    elif m == 7:                                # flames from the bottom
        yy = (sh.h - y) / sh.h
        n = math.sin(x * .3 + t * 8) + math.sin(x * .17 - t * 6) * .7 + math.sin(x * .5 + y * .2 + t * 10) * .3
        v = max(0.0, 1.05 - yy * 1.6 + n * .16)
        return (int(min(255, v * 480) * .6), int(min(255, max(0, v - .3) * 480) * .6), int(min(255, max(0, v - .85) * 400) * .6))
    elif m == 8:                                # aurora ribbons
        r = g = b = 0.0
        for k, base in enumerate((.32, .5, .66)):
            y0 = sh.h * base + math.sin(x * .05 + t * (.7 + k * .3) + k * 2) * sh.h * .1
            v = 1 / (1 + ((y - y0) / (sh.h * .06)) ** 2)
            cr, cg, cb = hue(90 + k * 70 + x * .4 + t * 15)
            r, g, b = r + cr * v, g + cg * v, b + cb * v
        return (min(255, int(r * .6)), min(255, int(g * .6)), min(255, int(b * .6) + 12))
    else:                                       # synthwave grid
        hz = sh.h * .5
        if y <= hz:
            k = y / hz
            return (int(20 + 150 * k * k), int(10 + 20 * k), int(50 + 60 * k))
        zz = hz / max(y - hz, .5)
        line = ((zz * 1.5 - t * 3) % 1) < .12 or ((((x - sh.w / 2) / sh.w) * zz * 8) % 1) < .07
        k = min(1.0, (y - hz) / (sh.h * .25))
        if line:
            return (int(255 * k), int(40 * k), int(200 * k))
        return (12, 0, 30)
    f = max(0.0, f)
    return (int(r * f), int(g * f), int(b * f))


def fill_color(sh, m, x, y, t):
    """color of the letter itself at pixel (x, y)"""
    if m == 0:
        return hue((x + y) * 2 + t * 70)
    if m == 1:
        r, g, b = hue(t * 40)
        f = .8 + .2 * math.sin(t * 5)
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
        return hue(t * 30 + (((x + y) // 6 + int(t * 4)) & 1) * 128)
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
        return hue(x * 512 / sh.w + t * 50)
    return hue(t * 30 + (((y // 6) + int(t * 8)) & 1) * 128)       # strobe
