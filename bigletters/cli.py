"""Command line: arguments, the interactive loop, the banner mode."""
import argparse
import math
import os
import random
import shutil
import sys
import time

from . import __version__
from . import font as F
from . import fx
from .fx import AXIS_NAMES, AXIS_SIZE, THEME_NAMES
from .gif import Recorder
from .show import Show
from .term import Painter, Terminal, detect_colors

FPS = 30
EFFECT_SECS = 2.5
AUTO_SECS = 5.0
MIN_COLS, MIN_ROWS = 12, 5
HELP = (" Space/→ next | ← back | Esc type text | Tab effects | ^L lock | ^T theme | ^F font | ^P pause "
        "| +/-/↑↓ speed | click, drag | ^C quit ")


def resolve(names, value, what):
    """--bg 3 / --bg plasma / --bg random -> index or None"""
    if value is None or value == "random":
        return None
    if value.isdigit() and int(value) < len(names):
        return int(value)
    if value in names:
        return names.index(value)
    sys.exit("bigletters: unknown %s '%s' (try --list-effects)" % (what, value))


def build_parser():
    ap = argparse.ArgumentParser(prog="bigletters", description="A random letter (or word, clock, countdown) fills the whole terminal.")
    ap.add_argument("--letters", metavar="LETTERS", help="pick random letters only from these (e.g. --letters claude)")
    ap.add_argument("--word", metavar="TEXT", help="start by showing this word or phrase")
    ap.add_argument("--file", metavar="PATH", help="show the words of this file one by one ('-' = stdin; piped stdin works too)")
    ap.add_argument("--auto", nargs="?", type=float, const=AUTO_SECS, metavar="SECONDS", help="change the text by itself (default every 5 s)")
    ap.add_argument("--theme", metavar="NAME", help="color theme: " + ", ".join(THEME_NAMES) + ", random")
    for axis in AXIS_SIZE:
        ap.add_argument("--" + axis, metavar="NAME", help="lock the %s effect (name or number, see --list-effects)" % axis)
    ap.add_argument("--font", metavar="NAME", help="letter style: " + ", ".join(F.FONT_NAMES) + ", random")
    ap.add_argument("--speed", type=float, default=1.0, metavar="X", help="animation speed (default 1)")
    ap.add_argument("--clock", action="store_true", help="show the time as a big clock")
    ap.add_argument("--countdown", type=float, metavar="SECONDS", help="count down from N seconds, then fireworks")
    ap.add_argument("--screensaver", action="store_true", help="auto mode, any key quits")
    ap.add_argument("--info", action="store_true", help="show the names of the current effects in the status line")
    ap.add_argument("--demo", action="store_true", help="a tour: --auto 4 --info")
    ap.add_argument("--banner", nargs="?", const="", metavar="TEXT",
                    help="print a banner into the scrollback and exit (no full screen); transparent background")
    ap.add_argument("--rows", type=int, default=6, metavar="N", help="banner height in terminal rows (default 6)")
    ap.add_argument("--record", metavar="FILE.gif", help="record the show to an animated GIF")
    ap.add_argument("--record-seconds", type=float, default=6.0, metavar="N", help="how long to record (default 6)")
    ap.add_argument("--colors", choices=("auto", "truecolor", "256", "16"), default="auto", help="color depth (default: detect)")
    ap.add_argument("--fps", type=int, default=FPS, metavar="N", help="frames per second (default %d; lower it over slow ssh)" % FPS)
    ap.add_argument("--no-mouse", action="store_true", help="do not capture the mouse")
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


def read_words(path):
    raw = sys.stdin.read() if path == "-" else open(path, encoding="utf-8", errors="ignore").read()
    words = [w for w in (F.clean(x) for x in raw.split()) if w]
    if not words:
        sys.exit("bigletters: no words to show")
    return words


def list_effects():
    for label, names in list(AXIS_NAMES.items()) + [("font", F.FONT_NAMES), ("theme", THEME_NAMES)]:
        print("%-6s %s" % (label, ", ".join("%d=%s" % (i, n) for i, n in enumerate(names))))


def pick_theme(name):
    name = name or "rainbow"
    if name == "random":
        name = random.choice(THEME_NAMES)
    if name not in fx.THEMES:
        sys.exit("bigletters: unknown theme '%s' (try --list-effects)" % name)
    fx.set_theme(name)
    return name


def banner(args, mode):
    """one still frame printed into the scrollback, letters only (transparent background)"""
    cols = max(MIN_COLS, shutil.get_terminal_size().columns)
    rows = max(2, min(args.rows, 20))
    text = F.clean(args.banner or "") or random.choice(F.LETTERS)
    font_i = resolve(F.FONT_NAMES, args.font, "font") or 0
    locks = {"deco": 0, "geo": 0, "intro": 0}
    for axis in ("fill",):
        v = resolve(AXIS_NAMES[axis], getattr(args, axis), axis)
        locks[axis] = v if v is not None else random.choice([0, 1, 2, 3, 5, 6, 7, 8])
    show = Show(cols, rows, text=text, locks=locks, font=font_i, transparent=True)
    show.born, show.flash, show.parts, show.fly = -100.0, 0.0, [], []
    grid = show.frame(random.uniform(1, 30))
    p = Painter(mode)
    sys.stdout.write("\n".join(p.render_lines(grid)) + "\n")
    sys.stdout.flush()


class App:
    """the interactive show"""

    def __init__(self, args, term, painter, show_kw):
        self.args, self.term, self.painter, self.kw = args, term, painter, show_kw
        self.clock_mode = args.clock or args.countdown is not None
        if args.demo and args.auto is None:
            args.auto = 4.0
        self.info = args.info or args.demo
        self.auto = None if self.clock_mode else (args.auto if args.auto is not None else (AUTO_SECS if args.screensaver else None))
        self.speed = max(.1, min(8.0, args.speed))
        self.cols, self.rows = term.size()
        self.show = Show(self.cols, self.rows, **show_kw)
        self.t = 0.0                                 # effective time: speed and pause apply
        self.paused = False
        self.next_fx = EFFECT_SECS
        self.next_auto = self.auto
        self.prompt = None                           # text being typed after Esc
        self.help_until = self.msg_until = 0.0
        self.msg = ""
        self.history = [self.show.text]
        self.hpos = 0
        self.font_random = args.font == "random"
        self.theme_i = THEME_NAMES.index(fx_theme_name())
        self.recorder = Recorder(args.record, args.record_seconds) if args.record else None
        self.cd_done = None
        self.last_burst = 0
        self.dragging = False
        self.frame_s = 1 / max(1, min(120, args.fps))
        self.force_full = True

    # ---- helpers
    def note(self, text):
        self.msg, self.msg_until = " " + text + " ", self.t + 2.0

    def advance(self):
        if self.args.bell:
            self.term.write("\a")
        return self.show.next_text()

    def show_text(self, text, remember=True):
        if text is None:
            return
        self.show.change(text, self.t)
        if remember and text != self.history[-1]:
            self.history = (self.history + [text])[-60:]
            self.hpos = len(self.history) - 1
        self.next_auto = self.t + self.auto if self.auto else None

    def rebuild(self):
        self.cols, self.rows = self.term.size()
        text = self.show.text
        self.show = Show(self.cols, self.rows, **dict(self.kw, text=text))
        self.painter.prev = None
        self.term.write("\x1b[2J")

    # ---- input
    def on_key(self, k):
        """returns True to quit"""
        a = self.args
        if k == "\x03":
            return True
        if self.prompt is not None:
            if k == "ESC":
                self.prompt = None
            elif k in ("\r", "\n"):
                word = F.clean(self.prompt)
                if word and not self.clock_mode:
                    self.show_text(word)
                self.prompt = None
            elif k in ("\x7f", "\b"):
                self.prompt = self.prompt[:-1]
            elif (k.upper() in F.BITS or k == " ") and len(self.prompt) < 40:
                self.prompt += k.upper()
            return False
        if k == "ESC":
            self.prompt = ""
        elif k == "\t":
            self.show.new_effects(self.t); self.next_fx = self.t + EFFECT_SECS
        elif k == "\x10":
            self.paused = not self.paused; self.note("paused" if self.paused else "resumed")
        elif k == "\x0c":
            self.show.all_locked = not self.show.all_locked
            self.note("effects locked" if self.show.all_locked else "effects unlocked")
        elif k == "\x14":
            self.theme_i = (self.theme_i + 1) % len(THEME_NAMES)
            fx.set_theme(THEME_NAMES[self.theme_i]); self.note("theme: " + THEME_NAMES[self.theme_i])
        elif k == "\x06":
            self.show.font = (self.show.font + 1) % len(F.FONT_NAMES)
            self.show.build_mask(); self.note("font: " + F.FONT_NAMES[self.show.font])
        elif k in ("+", "=", "UP"):
            self.speed = min(8.0, self.speed * 1.25); self.note("speed x%.2g" % self.speed)
        elif k in ("-", "_", "DOWN"):
            self.speed = max(.1, self.speed / 1.25); self.note("speed x%.2g" % self.speed)
        elif k == "?":
            self.help_until = self.t + 6 if self.help_until <= self.t else 0
        elif self.clock_mode:
            pass
        elif k == "LEFT":
            if self.hpos > 0:
                self.hpos -= 1
                self.show_text(self.history[self.hpos], remember=False)
        elif k == "RIGHT" or k in (" ", "\r", "\n"):
            if k == "RIGHT" and self.hpos < len(self.history) - 1:
                self.hpos += 1
                self.show_text(self.history[self.hpos], remember=False)
            else:
                self.show_text(self.advance())
        elif k.upper() in F.BITS:
            self.show_text(k.upper())
        return False

    def on_mouse(self, button, x, y, pressed):
        px, py = x - 1, (y - 1) * 2
        if button in (64, 65):                       # wheel
            self.on_key("UP" if button == 64 else "DOWN")
        elif button & 32 and self.dragging:          # drag: sparks follow the cursor
            self.show.sparks(px, py, 4)
        elif button & 3 == 0 and not button & 32:
            if pressed:
                self.dragging = True
                self.show.burst(px, py, 40)
                if not self.clock_mode and self.prompt is None:
                    self.show_text(self.advance())
            else:
                self.dragging = False

    def handle_events(self):
        for ev in self.term.events():
            if self.args.screensaver and self.prompt is None and (ev[0] != "mouse" or ev[4] and not ev[1] & 32):
                return True
            kind = ev[0]
            if kind == "key":
                if self.on_key(ev[1]):
                    return True
            elif kind == "esc":
                if self.on_key("ESC"):
                    return True
            elif kind == "arrow":
                if self.on_key({"A": "UP", "B": "DOWN", "C": "RIGHT", "D": "LEFT"}[ev[1]]):
                    return True
            elif kind == "mouse":
                self.on_mouse(*ev[1:])
        return False

    # ---- one tick
    def tick(self, dt):
        a, show, t = self.args, self.show, self.t
        if self.clock_mode:                          # new text once a second; fireworks at zero
            if a.clock:
                text = fmt_clock()
            else:
                left = a.countdown - t
                text = fmt_countdown(left) if left > 0 else "GO!"
            if text != show.text:
                show.set_text(text, t, quiet=(text != "GO!"))
                if text == "GO!":
                    self.cd_done = t
            if self.cd_done is not None and t - self.cd_done < 3 and int((t - self.cd_done) * 3) != self.last_burst:
                self.last_burst = int((t - self.cd_done) * 3)
                show.burst(random.uniform(.15, .85) * show.w, random.uniform(.15, .6) * show.h, 70)
        elif self.auto and self.next_auto is not None and t >= self.next_auto:
            show.new_effects(t)
            if self.font_random:
                show.font = random.randrange(len(F.FONT_NAMES))
                show.build_mask()
            self.show_text(self.advance())
            self.next_fx = t + EFFECT_SECS
        elif t >= self.next_fx:
            show.new_effects(t); self.next_fx = t + EFFECT_SECS
        show.step(0.0 if self.paused else dt * self.speed, t)

    def status(self):
        if self.prompt is not None:
            return " Type a letter or word, Enter = show, Esc = cancel:  %s_" % self.prompt
        if self.t < self.help_until:
            return HELP
        if self.t < self.msg_until:
            return self.msg
        if self.info:
            sh = self.show
            return " bg:%s fill:%s geo:%s deco:%s intro:%s font:%s theme:%s " % (
                fx.BG_NAMES[sh.bg], fx.FILL_NAMES[sh.fill], fx.GEO_NAMES[sh.geo], fx.DECO_NAMES[sh.deco],
                fx.INTRO_NAMES[sh.intro], F.FONT_NAMES[sh.font], THEME_NAMES[self.theme_i])
        return None

    def run(self):
        a, term = self.args, self.term
        if self.clock_mode:
            self.show.set_text(fmt_clock() if a.clock else fmt_countdown(a.countdown), 0.0)
        if self.recorder:
            self.note("recording %s for %gs" % (a.record, a.record_seconds))
        last = time.time()
        while True:
            wall = time.time()
            dt = min(wall - last, .1)
            last = wall
            if a.time and self.t > a.time:
                return
            if not self.paused:
                self.t += dt * self.speed
            if term.resized or term.size() != (self.cols, self.rows):
                term.resized = False
                self.rebuild()
            if self.handle_events():
                return
            self.tick(dt)
            t0 = time.time()
            grid = self.show.frame(self.t)
            if self.recorder:
                self.recorder.add(grid, self.t)
            term.write(self.painter.paint(grid, self.status(), full=self.force_full))
            self.force_full = False
            # adaptive quality: bigger blocks when the terminal is too big for this machine
            spent = time.time() - t0
            if spent > self.frame_s * 1.4 and self.show.q < 4:
                self.show.q += 1
            elif spent < self.frame_s * .4 and self.show.q > 1:
                self.show.q -= 1
            time.sleep(max(0, self.frame_s - (time.time() - wall)))


def fx_theme_name():
    for name, v in fx.THEMES.items():
        if v == fx.THEME:
            return name
    return "rainbow"


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.list_effects:
        list_effects()
        return
    locks = {}
    for axis, names in AXIS_NAMES.items():
        v = resolve(names, getattr(args, axis), axis)
        if v is not None:
            locks[axis] = v
    font_i = resolve(F.FONT_NAMES, args.font, "font") or 0
    if args.font == "random":
        font_i = random.randrange(len(F.FONT_NAMES))
    pick_theme(args.theme or ("random" if args.banner is not None else None))
    mode = detect_colors() if args.colors == "auto" else args.colors
    if args.banner is not None:
        banner(args, mode)
        return
    clock_mode = args.clock or args.countdown is not None
    words = []
    if args.file or (not sys.stdin.isatty() and not clock_mode):
        words = read_words(args.file or "-")
    if not sys.stdout.isatty():
        sys.exit("bigletters: run it in a real terminal (or use --banner)")
    cols, rows = shutil.get_terminal_size()
    if cols < MIN_COLS or rows < MIN_ROWS:
        sys.exit("bigletters: the terminal is too small (%dx%d)" % (cols, rows))
    show_kw = dict(pool=sorted(set(F.clean(args.letters or "")) - {" "}) or None, text=F.clean(args.word or "") or None,
                   words=words, locks=locks, font=font_i)
    painter = Painter(mode)
    with Terminal(mouse=not args.no_mouse) as term:
        app = App(args, term, painter, show_kw)
        try:
            app.run()
        except KeyboardInterrupt:
            pass
    if app.recorder:
        saved = app.recorder.save()
        print("saved %s (%d frames)" % (saved, len(app.recorder.frames)) if saved else "nothing recorded")
