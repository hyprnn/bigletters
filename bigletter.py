#!/usr/bin/env python3
"""bigletter - a random English letter (or a word) fills the whole terminal,
with colors, effects and animations. Pure Python 3, no dependencies.

  Space / Enter  new random letter      Tab  switch effects
  any letter     show that letter       Esc  type your own letter or word
  Ctrl+C         quit                   (in the prompt: Enter = ok, Esc = cancel)

Flags:  --letters claude   random letters come only from c, l, a, u, d, e
        --word claude      start by showing this word
        --auto [SECONDS]   change the letter by itself (every 5 s by default)

Needs a truecolor terminal (most modern ones). Run:  python3 bigletter.py
"""
import argparse, math, os, random, shutil, sys, time

try:
    import select, termios, tty
    POSIX = True
except ImportError:          # Windows
    import msvcrt
    POSIX = False

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
}
BITS = {k: [[int(c) for c in row] for row in v.split()] for k, v in GLYPHS.items()}

N_BG, N_FILL, N_GEO = 10, 10, 9
FX_SECS, FPS = 2.5, 25


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
    return HUE[int(h) & 255]


def blur(src, w, h, r):
    """box blur, two passes (rows then columns) with sliding sums"""
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


def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


class Show:
    def __init__(self, w, h, pool=None, text=None):
        self.w, self.h = w, h * 2           # pixels: each cell = 2 half-block pixels
        self.pool = pool or sorted(BITS)
        self.letter = None
        self.bg, self.fill, self.geo = (random.randrange(N_BG), random.randrange(N_FILL), random.randrange(N_GEO))
        self.parts = []
        self.t0 = time.time()
        self.flash = 0.0
        self.set_letter(text or self.random_letter(), 0)

    def random_letter(self):
        opts = [c for c in self.pool if c != self.letter] or self.pool
        return random.choice(opts)

    def set_letter(self, ch, now):
        self.letter, self.born, self.flash = ch, now, 0.55
        self.build_mask()
        self.burst(self.w / 2, self.h / 2, 60)

    def build_mask(self):
        W, H = self.w, self.h
        n = len(self.letter)
        cols = n * 6 - 1                              # 5 columns per letter + 1 gap
        g = [[0] * cols for _ in range(7)]
        for k, ch in enumerate(self.letter):
            if ch in BITS:
                for y in range(7):
                    g[y][k * 6:k * 6 + 5] = BITS[ch][y]
        stretch = 1.7                                  # a bit wide: fills wide terminals
        bh = H * 0.9
        bw = bh * cols / 7 * stretch
        if bw > W * 0.9:                               # long word: keep the shape, shrink
            bw = W * 0.9
            bh = bw * 7 / (cols * stretch)
        x0, y0 = (W - bw) / 2, (H - bh) / 2
        def px(ix, iy):
            return g[iy][ix] if 0 <= ix < cols and 0 <= iy < 7 else 0
        m = []
        for y in range(H):
            fy = (y - y0) / bh * 7 - 0.5
            iy, wy = math.floor(fy), fy - math.floor(fy)
            for x in range(W):
                fx = (x - x0) / bw * cols - 0.5
                ix, wx = math.floor(fx), fx - math.floor(fx)
                v = (px(ix, iy) * (1 - wx) + px(ix + 1, iy) * wx) * (1 - wy) + \
                    (px(ix, iy + 1) * (1 - wx) + px(ix + 1, iy + 1) * wx) * wy
                m.append(smooth(0.3, 0.7, v))
        self.mask = m
        self.glow = [min(1.0, v * 2.2) for v in blur(m, W, H, max(2, W // 45))]

    def burst(self, x, y, n):
        for _ in range(n):
            a, s = random.random() * 6.283, random.uniform(8, 40)
            self.parts.append([x, y, math.cos(a) * s, math.sin(a) * s * 0.6 - 6, random.uniform(0.7, 1.6), random.randrange(256)])

    def new_effects(self):
        self.bg = (self.bg + random.randrange(1, N_BG)) % N_BG
        self.fill = (self.fill + random.randrange(1, N_FILL)) % N_FILL
        self.geo = (self.geo + random.randrange(1, N_GEO)) % N_GEO

    # ---- colors ----
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
            d = math.hypot(x - self.w / 2, (y - self.h / 2) * 1.0)
            r, g, b = hue(d * 5 - t * 90)
            f = .2 + .12 * math.sin(d * .4 - t * 3)
        elif m == 5:                                # starfield, 3 parallax layers
            for layer, sp in ((0, 6), (1, 14), (2, 30)):
                hh = (((x + int(t * sp)) * 73856093) ^ (y * 19349663) ^ (layer * 83492791)) & 0xffff
                if hh < 110:
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
        elif m == 9:                                # synthwave grid
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
        else:                                       # checkers + wave
            cx = int((x + math.sin(y * .3 + t * 2) * 2) // 4)
            cy = int((y + math.sin(x * .2 + t * 2) * 2) // 4)
            r, g, b = hue(t * 40 + ((cx + cy) & 1) * 120)
            f = .3 if (cx + cy) & 1 else .12
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
            return (min(255, r + 30), min(255, g + 20), b)
        if m == 4:
            st = ((x + y) // 6 + int(t * 4)) & 1
            return hue(t * 30 + st * 128)
        if m == 6:                                  # rainbow with glitter
            if ((x * 73856093 ^ y * 19349663 ^ int(t * 12) * 83492791) & 0xffff) % 30 == 0:
                return (255, 255, 255)
            return hue((x + y) * 2 + t * 70)
        if m == 7:                                  # chrome
            b_ = .5 + .5 * math.sin(y * .5 + t * 2 + x * .05)
            if b_ > .92:
                return (255, 255, 255)
            return (int(b_ * 200 + 30), int(b_ * 215 + 40), int(b_ * 235 + 20))
        if m == 8:                                  # rainbow across the width
            return hue(x * 512 / self.w + t * 50)
        if m == 5:                                  # outline: bright edge
            return hue(t * 60 + y * 2)
        st = ((y // 6) + int(t * 8)) & 1            # strobe
        return hue(t * 30 + st * 128)

    # ---- frame ----
    def frame(self, now):
        W, H = self.w, self.h
        t = now
        age = t - self.born
        scale = 1.0
        if age < .55:
            x = age / .55 - 1
            scale = 1 + 2.70158 * x ** 3 + 1.70158 * x * x
        scale *= 1 + .05 * math.sin(t * 3)
        scale = max(scale, .02)
        geo = self.geo
        rot = math.cos(t * 1.1) if geo == 2 else None
        gl_on = geo == 3 and (int(t * 8) // 5) % 3 != 0
        cx, cy = W / 2, H / 2
        offx = 0.0
        offy = math.sin(t * 2.3) * H * .06 if geo == 3 else 0
        rowoff = [0.0] * H
        if geo == 1:
            rowoff = [math.sin(y * .35 + t * 5) * W * .035 for y in range(H)]
        elif gl_on:
            gt = int(t * 8)
            for y in range(H):
                hh = ((y // 4) * 73856093 ^ gt * 19349663) & 0xffff
                if hh % 4 == 0:
                    rowoff[y] = (hh % 17 - 8) * W / 90
        if geo == 4:                                 # bounce
            offy = H * .06 - abs(math.sin(t * 3)) * H * .14
        elif geo == 5:                               # big zoom pulse
            scale *= .78 + .27 * math.sin(t * 2.2)
        elif geo == 6:                               # shear
            sh = math.sin(t * 2) * .5
            rowoff = [(y - cy) * sh for y in range(H)]
        elif geo == 8:                               # orbit
            offx, offy = math.cos(t * 1.7) * W * .07, math.sin(t * 1.7) * H * .07
        scale = max(scale, .02)
        sx = 1 / scale
        if rot is not None:
            sx = 1 / (scale * max(abs(rot), .06)) * (1 if rot >= 0 else -1)
        sy = 1 / scale
        if geo == 7:                                 # jelly: squash and stretch
            j = .2 * math.sin(t * 5)
            sx, sy = sx / (1 + j), sy / (1 - j)
        mask, glow = self.mask, self.glow
        fl = self.flash
        out = []
        for ty in range(0, H, 2):
            row = []
            for half in (0, 1):
                pass
            line = []
            for x in range(W):
                cols = []
                for y in (ty, ty + 1):
                    v = int((y - cy - offy) * sy + cy)
                    u = int((x - cx - offx) * sx + cx + rowoff[y])
                    m = g = 0.0
                    if 0 <= u < W and 0 <= v < H:
                        i = v * W + u
                        m, g = mask[i], glow[i]
                    r, gg, b = self.bgc(x, y, t)
                    if g > .01:
                        gr, ggg, gb = hue(t * 40 + 40)
                        k = g * (1 - m) * .8
                        r, gg, b = r + gr * k, gg + ggg * k, b + gb * k
                    if self.fill == 5:
                        m = max(0.0, 1 - abs(m - .5) * 2.4)
                    if m > .01:
                        fr, fg, fb = self.fillc(x, y, t)
                        r, gg, b = r + (fr - r) * m, gg + (fg - gg) * m, b + (fb - b) * m
                    if fl > 0:
                        r, gg, b = r + 255 * fl, gg + 255 * fl, b + 255 * fl
                    cols.append((max(0, min(255, int(r))), max(0, min(255, int(gg))), max(0, min(255, int(b)))))
                line.append(cols)
            out.append(line)
        # sparks
        for p in self.parts:
            x, y = int(p[0]), int(p[1])
            if 0 <= x < W and 0 <= y < H:
                c = (255, 255, 255) if int(t * 10 + p[5]) % 4 == 0 else hue(p[5] + t * 60)
                out[y // 2][x][y & 1] = c
        return out

    def step(self, dt):
        self.flash = max(0.0, self.flash - dt * 2.5)
        for p in self.parts:
            p[0] += p[2] * dt; p[1] += p[3] * dt; p[3] += 25 * dt; p[4] -= dt
        self.parts = [p for p in self.parts if p[4] > 0]
        for _ in range(2):                           # sparks fall off the letter
            x, y = random.randrange(self.w), random.randrange(self.h)
            if self.mask[y * self.w + x] > .7 and len(self.parts) < 300:
                self.parts.append([x, y, random.uniform(-6, 6), random.uniform(-14, -2), random.uniform(.4, 1), random.randrange(256)])


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


def read_keys():
    keys = []
    if POSIX:
        while select.select([sys.stdin], [], [], 0)[0]:
            ch = os.read(sys.stdin.fileno(), 32).decode(errors="ignore")
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


def main():
    ap = argparse.ArgumentParser(description="A random letter fills the whole terminal.")
    ap.add_argument("--auto", nargs="?", type=float, const=5.0, default=None, metavar="SECONDS",
                    help="change the letter automatically (default every 5 s)")
    ap.add_argument("--letters", default=None, metavar="LETTERS",
                    help="pick random letters only from these (e.g. --letters claude)")
    ap.add_argument("--word", default=None, metavar="WORD", help="start by showing this word")
    ap.add_argument("--time", type=float, default=None, metavar="SECONDS", help="quit after N seconds")
    args = ap.parse_args()
    limit = args.time
    clean = lambda txt: "".join(c for c in txt.upper() if c in BITS or c == " ").strip()
    pool = sorted(set(clean(args.letters or "")) - {" "}) or None
    first = clean(args.word or "") or None
    if not (sys.stdout.isatty() and sys.stdin.isatty()):
        sys.exit("bigletter: run it in a real terminal")
    old = termios.tcgetattr(sys.stdin) if POSIX else None
    if POSIX:
        tty.setcbreak(sys.stdin.fileno())
    sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[2J")
    try:
        size = shutil.get_terminal_size()
        show = Show(size.columns, size.lines, pool, first)
        start = last = time.time()
        next_fx = FX_SECS
        next_letter = args.auto
        prompt = None                                # text being typed after Esc, or None
        while True:
            now = time.time()
            t = now - start
            if limit and t > limit:
                break
            cur = shutil.get_terminal_size()
            if cur != size:
                size = cur
                letter = show.letter
                show = Show(size.columns, size.lines, pool)
                show.t0 = start
                show.set_letter(letter, t)
                sys.stdout.write("\x1b[2J")
            for k in read_keys():
                if k == "\x03":
                    return
                if prompt is not None:                # typing a letter / word
                    if k == "ESC":
                        prompt = None
                    elif k in ("\r", "\n"):
                        word = clean(prompt)
                        if word:
                            show.set_letter(word, t)
                            if args.auto: next_letter = t + args.auto
                        prompt = None
                    elif k in ("\x7f", "\b"):
                        prompt = prompt[:-1]
                    elif k.isascii() and (k.isalpha() or k == " ") and len(prompt) < 40:
                        prompt += k.upper()
                    continue
                if k == "ESC":
                    prompt = ""
                elif k == "\t":
                    show.new_effects(); next_fx = t + FX_SECS
                elif k.isascii() and k.isalpha():
                    show.set_letter(k.upper(), t)
                    if args.auto: next_letter = t + args.auto
                elif k in (" ", "\r", "\n"):
                    show.set_letter(show.random_letter(), t)
            if args.auto and t >= next_letter:
                show.new_effects()
                show.set_letter(show.random_letter(), t)
                next_letter, next_fx = t + args.auto, t + FX_SECS
            elif t >= next_fx:
                show.new_effects(); next_fx = t + FX_SECS
            show.step(min(now - last, .1)); last = now
            status = None if prompt is None else \
                " Type a letter or word, Enter = show, Esc = cancel:  %s_" % prompt
            paint(show.frame(t), status)
            time.sleep(max(0, 1 / FPS - (time.time() - now)))
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
        if POSIX:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)


if __name__ == "__main__":
    main()
