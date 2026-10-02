"""The show: everything that is drawn (letter, effects, particles) as a grid of colors."""
import math
import random

from . import font as F
from . import fx
from .fx import smooth, hue, tri_hash, N_BG, N_FILL, N_GEO, N_DECO, N_INTRO, AXIS_SIZE

FX_FADE = .9          # seconds an effect change cross-fades


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


class Show:
    def __init__(self, w, h, pool=None, text=None, words=None, locks=None, font=0, transparent=False):
        self.w, self.h = w, h * 2                    # pixels: a cell = 2 half-block pixels
        self.pool = pool or list(F.LETTERS)
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
        self.transparent = transparent
        self.born = 0.0
        self.outro_t0 = None
        self.pending = None
        self.mask = self.glow = self.core = self.lit = None
        self.box = (0, 0, self.w, self.h)
        self._polar = None
        self._vig = None
        self.cols_delay = [0.0] * self.w
        self.bg = random.randrange(N_BG)
        self.fill = random.randrange(N_FILL)
        self.geo = random.randrange(N_GEO)
        self.deco = random.choice([0, 0, 1, 2, 3])
        self.intro = random.randrange(N_INTRO)
        self.apply_locks()
        self.prev = {"bg": self.bg, "fill": self.fill, "geo": self.geo}
        self.fx_t0 = None
        self.set_text(text or self.next_text(), 0.0)

    def apply_locks(self):
        for axis, v in self.locks.items():
            setattr(self, axis, v)

    # ---- cached per-size maps
    def polar(self):
        if self._polar is None:
            W, H = self.w, self.h
            cx, cy = W / 2, H / 2
            dist, ang = [0.0] * (W * H), [0.0] * (W * H)
            for y in range(H):
                for x in range(W):
                    dx, dy = x - cx, y - cy
                    dist[y * W + x] = math.hypot(dx, dy)
                    ang[y * W + x] = math.atan2(dy, dx)
            self._polar = (dist, ang)
        return self._polar

    def vignette(self):
        if self._vig is None:
            W, H = self.w, self.h
            self._vig = [1 - .38 * (((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2) / 2
                         for y in range(H) for x in range(W)]
        return self._vig

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
        m = F.build_masks(self.text, W, H, F.FONT_NAMES[self.font])
        self.mask, self.core, self.box = m["alpha"], m["core"], m["box"]
        mask, core, R = self.mask, self.core, m["R"]
        # light from the top left: pseudo normal from the gradient of the core field
        lit = [1.0] * (W * H)
        k = .38 * R / 2
        for y in range(1, H - 1):
            row = y * W
            for x in range(1, W - 1):
                i = row + x
                if mask[i] > .02:
                    v = 1 + k * ((core[i + 1] - core[i - 1]) + (core[i + W] - core[i - W]))
                    lit[i] = .55 if v < .55 else (1.45 if v > 1.45 else v)
        self.lit = lit
        self.glow = [min(1.0, v * 2.2) for v in blur(mask, W, H, max(2, W // 45))]

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

    def sparks(self, x, y, n=4):
        """a few sparks at a pixel position (mouse drag)"""
        for _ in range(n):
            self.parts.append([x + random.uniform(-1, 1), y + random.uniform(-1, 1), random.uniform(-14, 14),
                               random.uniform(-18, 2), random.uniform(.4, .9), random.randrange(256)])

    def make_fly(self):
        for _ in range(min(260, max(60, self.w * self.h // 40))):
            tx, ty = self.random_letter_point()
            edge = random.randrange(4)
            sx = random.randrange(self.w) if edge < 2 else (0 if edge == 2 else self.w - 1)
            sy = (0 if edge == 0 else self.h - 1) if edge < 2 else random.randrange(self.h)
            self.fly.append((sx, sy, tx, ty, random.randrange(256)))

    # ---- effects
    def new_effects(self, t=None):
        """pick fresh effects for every axis that is not locked; with t they cross-fade"""
        if self.all_locked:
            return
        self.prev = {"bg": self.bg, "fill": self.fill, "geo": self.geo}
        self.fx_t0 = t
        for axis, n in AXIS_SIZE.items():
            if axis in self.locks or axis == "intro":
                continue
            cur = getattr(self, axis)
            if axis == "deco":
                setattr(self, axis, random.choices(range(n), [4, 2, 2, 2])[0])
            else:
                setattr(self, axis, (cur + random.randrange(1, n)) % n)

    def geo_params(self, geo, t):
        """motion at time t -> (scale, offx, offy, xscale, yscale, alpha, rowoffsets|None); forward scales"""
        W, H = self.w, self.h
        cy = H / 2
        sc, ox, oy, fxs, fys, al, ro = 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, None
        if geo == 1:                                 # wave
            ro = [math.sin(y * .35 + t * 5) * W * .035 for y in range(H)]
        elif geo == 2:                               # spin around the vertical axis
            c = math.cos(t * 1.1)
            fxs = c if abs(c) > .06 else (.06 if c >= 0 else -.06)
        elif geo == 3:                               # glitch
            oy = math.sin(t * 2.3) * H * .06
            if (int(t * 8) // 5) % 3 != 0:
                gt = int(t * 8)
                ro = [((tri_hash(y // 4, gt) % 17 - 8) * W / 90) if tri_hash(y // 4, gt) % 4 == 0 else 0.0 for y in range(H)]
        elif geo == 4:                               # bounce
            oy = H * .06 - abs(math.sin(t * 3)) * H * .14
        elif geo == 5:                               # big zoom pulse
            sc = .78 + .27 * math.sin(t * 2.2)
        elif geo == 6:                               # shear
            sh = math.sin(t * 2) * .5
            ro = [(y - cy) * sh for y in range(H)]
        elif geo == 7:                               # jelly
            j = .2 * math.sin(t * 5)
            fxs, fys = 1 + j, 1 - j
        elif geo == 8:                               # orbit
            ox, oy = math.cos(t * 1.7) * W * .07, math.sin(t * 1.7) * H * .07
        elif geo == 9:                               # fly in from the distance, again and again
            ph = (t * .35) % 1
            sc = .04 + 1.12 * ph ** 2
            al = 1 - smooth(.85, 1.0, ph)
        return sc, ox, oy, fxs, fys, al, ro

    # ---- frame
    def frame(self, t):
        """-> grid of rows of (top, bottom) colors, one entry per terminal cell (None = transparent)"""
        W, H = self.w, self.h
        age = t - self.born
        deco, intro = self.deco, self.intro
        P = self.geo_params(self.geo, t)
        k = 1.0
        if self.fx_t0 is not None and t - self.fx_t0 < FX_FADE:
            k = smooth(0, 1, (t - self.fx_t0) / FX_FADE)
        if k < 1:                                    # motion eases from the old effect to the new one
            Q = self.geo_params(self.prev["geo"], t)
            sc, ox, oy, fxs, fys, al = (Q[i] + (P[i] - Q[i]) * k for i in range(6))
            ro1, ro2 = P[6], Q[6]
            ro = None if ro1 is None and ro2 is None else [
                (ro2[y] if ro2 else 0.0) * (1 - k) + (ro1[y] if ro1 else 0.0) * k for y in range(H)]
        else:
            sc, ox, oy, fxs, fys, al, ro = P
        scale = 1.0
        if intro == 0 and age < .55:
            x = age / .55 - 1
            scale = max(.02, 1 + 2.70158 * x ** 3 + 1.70158 * x * x)
        scale *= (1 + .05 * math.sin(t * 3)) * sc
        cx, cy = W / 2, H / 2
        offx, offy = ox, oy
        alpha_mul = al
        rowoff = ro or [0.0] * H
        ym = H * .66
        if deco == 3:                                # mirror: smaller letter above a water line
            scale *= .62
            offy -= H * .13
        scale = max(scale, .02)
        sx, sy = 1 / (scale * fxs), 1 / (scale * fys)
        mask, glow, core, lit, vig = self.mask, self.glow, self.core, self.lit, self.vignette()
        fl = self.flash
        transparent = self.transparent
        fill_mode, bg_mode = self.fill, self.bg
        fill5 = fill_mode == 5
        old_bg, old_fill = self.prev["bg"], self.prev["fill"]
        fade_fx = k < 1

        # intro visibility
        type_p = None
        if self.outro_t0 is not None:
            type_p = max(0.0, 1 - (t - self.outro_t0) / .45)
        elif intro == 1 and age < .25 + .12 * len(self.text):
            type_p = age / (.25 + .12 * len(self.text))
        bx0, by0, bx1, by1 = self.box
        revx = bx0 + (type_p if type_p is not None else 1) * (bx1 - bx0)
        asm = smooth(.9, 1.5, age) if intro == 2 and age < 1.5 else 1.0
        dropping = intro == 3 and age < 1.3
        delays = self.cols_delay
        ex_a = t * .9
        ex_dx, ex_dy = math.cos(ex_a), math.sin(ex_a) * .6
        q = self.q
        bg_color, fill_color = fx.bg_color, fx.fill_color

        def sample(x, y):
            """(mask, glow, core, lit) of the letter at screen pixel (x, y)"""
            v = int((y - cy - offy) * sy + cy)
            u = int((x - cx - offx) * sx + cx + rowoff[y])
            if 0 <= u < W and 0 <= v < H:
                i = v * W + u
                return mask[i], glow[i], core[i], lit[i]
            return 0.0, 0.0, 0.0, 1.0

        pix = [[None] * W for _ in range(H)]
        for y0 in range(0, H, q):
            for x0 in range(0, W, q):
                xc, yc = min(x0 + q // 2, W - 1), min(y0 + q // 2, H - 1)
                if transparent:
                    bgc = (0, 0, 0)
                else:
                    bgc = bg_color(self, bg_mode, xc, yc, t)
                    if fade_fx:
                        ob = bg_color(self, old_bg, xc, yc, t)
                        bgc = (ob[0] + (bgc[0] - ob[0]) * k, ob[1] + (bgc[1] - ob[1]) * k, ob[2] + (bgc[2] - ob[2]) * k)
                    vv = vig[yc * W + xc]
                    bgc = (bgc[0] * vv, bgc[1] * vv, bgc[2] * vv)
                fc = None
                for y in range(y0, min(y0 + q, H)):
                    row = pix[y]
                    refl = deco == 3 and y > ym
                    if refl:
                        ysrc = 2 * ym - y + math.sin(y * .6 + t * 4) * 1.2
                        ysrc = min(max(int(ysrc), 0), H - 1)
                    else:
                        ysrc = y
                    for x in range(x0, min(x0 + q, W)):
                        # --- the letter at this pixel
                        v = int((ysrc - cy - offy) * sy + cy)
                        u = int((x - cx - offx) * sx + cx + rowoff[ysrc])
                        if 0 <= u < W and 0 <= v < H:
                            i = v * W + u
                            m, g, c, lt = mask[i], glow[i], core[i], lit[i]
                        else:
                            m = g = c = 0.0
                            lt = 1.0
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
                        if vis != 1.0:
                            m, g = m * vis, g * vis
                        if refl:
                            m, g = m * .35, g * .3
                        if transparent:
                            g = 0.0
                        r, gg, b = bgc
                        if deco == 3:
                            if y > ym:
                                r, gg, b = r * .7, gg * .75, b * .9 + 10
                            elif abs(y - ym) < 1:
                                r, gg, b = 150, 200, 255
                        if deco in (1, 2) and m < .5 and g > .04:      # 3D side / long shadow
                            steps = 6 if deco == 1 else 10
                            reach = H * (.05 if deco == 1 else .15)
                            dx, dy = (ex_dx, ex_dy) if deco == 1 else (.7, .7)
                            for kk in range(1, steps + 1):
                                d = reach * kk / steps
                                sm, _, _, _ = sample(int(x - dx * d), min(max(int(y - dy * d), 0), H - 1))
                                if sm * vis > .5:
                                    if deco == 1:
                                        fr, fg, fb = fill_color(self, fill_mode, x, y, t)
                                        f = .3 + .35 * (1 - kk / steps)
                                        r, gg, b = fr * f, fg * f, fb * f
                                        m, g = 1.0, 0.0
                                        c = 0.0
                                        lt = 1.0
                                    else:
                                        f = .3 + .5 * kk / steps
                                        r, gg, b = r * f, gg * f, b * f
                                    break
                        if g > .01:
                            gr, ggg, gb = hue(t * 40 + 40)
                            kg = g * (1 - m) * .8
                            r, gg, b = r + gr * kg, gg + ggg * kg, b + gb * kg
                        if fill5:
                            m = m * (1 - smooth(.05, .5, c))
                        if m > .01:
                            if fc is None or q == 1 or deco == 1:
                                fc = fill_color(self, fill_mode, x, y, t)
                                if fade_fx:
                                    of = fill_color(self, old_fill, x, y, t)
                                    fc = (of[0] + (fc[0] - of[0]) * k, of[1] + (fc[1] - of[1]) * k, of[2] + (fc[2] - of[2]) * k)
                            fr, fg, fb = fc
                            if fill_mode == 1:                       # neon tube: white hot center
                                wc = c * c * .75
                                fr, fg, fb = fr + (255 - fr) * wc, fg + (255 - fg) * wc, fb + (255 - fb) * wc
                            fr, fg, fb = fr * lt, fg * lt, fb * lt
                            if refl:
                                fr, fg, fb = fr * .8, fg * .85, fb
                            r, gg, b = r + (fr - r) * m, gg + (fg - gg) * m, b + (fb - b) * m
                            if head:
                                r, gg, b = 210, 255, 220
                        if type_p is not None and by0 <= y <= by1 and 0 < x - revx < 2 and (type_p < 1 or int(t * 2) % 2 == 0):
                            r, gg, b = 255, 255, 255             # typewriter cursor
                        if fl > 0:
                            r, gg, b = r + 255 * fl, gg + 255 * fl, b + 255 * fl
                        if transparent and m < .04 and g < .04 and fl <= 0:
                            row[x] = None
                        else:
                            row[x] = (max(0, min(255, int(r))), max(0, min(255, int(gg))), max(0, min(255, int(b))))
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
        for p in self.parts:                         # sparks, with a short fading trail
            x, y, vx, vy, life, hh = p
            if 0 <= int(x) < W and 0 <= int(y) < H:
                fade = min(1.0, life / .35)
                col = (255, 255, 255) if int(t * 10 + hh) % 4 == 0 else hue(hh + t * 60)
                pix[int(y)][int(x)] = (int(col[0] * fade), int(col[1] * fade), int(col[2] * fade))
                tx_, ty_ = int(x - vx * .035), int(y - vy * .035)
                if 0 <= tx_ < W and 0 <= ty_ < H and (tx_, ty_) != (int(x), int(y)) and pix[ty_][tx_] is not None:
                    o = pix[ty_][tx_]
                    pix[ty_][tx_] = tuple(min(255, int(o[j] + col[j] * .35 * fade)) for j in range(3))
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
        if self.pending is None and dt > 0 and not self.transparent:
            for _ in range(2):                       # sparks fall off the letter
                if len(self.parts) < 300:
                    x, y = random.randrange(self.w), random.randrange(self.h)
                    if self.on_letter(x, y):
                        self.parts.append([x, y, random.uniform(-6, 6), random.uniform(-14, -2), random.uniform(.4, 1), random.randrange(256)])
