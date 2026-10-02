"""Terminal: color depth detection, diff-based painting, keyboard + mouse input."""
import os
import re
import signal
import sys

try:
    import select, termios, tty
    POSIX = True
except ImportError:          # Windows
    import msvcrt
    POSIX = False

# ------------------------------------------------------------------ colors
_CUBE = (0, 95, 135, 175, 215, 255)
ANSI16 = [(0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0), (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229),
          (127, 127, 127), (255, 0, 0), (0, 255, 0), (255, 255, 0), (92, 92, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255)]


def detect_colors(env=None):
    """'truecolor', '256' or '16' from the environment (BIGLETTERS_COLORS overrides)"""
    env = os.environ if env is None else env
    forced = env.get("BIGLETTERS_COLORS", "").lower()
    if forced in ("truecolor", "256", "16"):
        return forced
    ct = env.get("COLORTERM", "").lower()
    term = env.get("TERM", "").lower()
    prog = env.get("TERM_PROGRAM", "")
    if ct in ("truecolor", "24bit") or "truecolor" in term or "24bit" in term or "direct" in term:
        return "truecolor"
    if prog in ("iTerm.app", "WezTerm", "vscode", "ghostty", "Hyper") or env.get("WT_SESSION") or env.get("KONSOLE_VERSION") \
            or env.get("VTE_VERSION") or term in ("xterm-kitty", "alacritty", "foot", "xterm-ghostty", "wezterm"):
        return "truecolor"
    if "256" in term:
        return "256"
    if term in ("linux", "vt100", "ansi", "dumb"):
        return "16"
    return "256"


def _near256(r, g, b):
    def lvl(v):
        return min(range(6), key=lambda i: abs(_CUBE[i] - v))
    ri, gi, bi = lvl(r), lvl(g), lvl(b)
    cube = (_CUBE[ri], _CUBE[gi], _CUBE[bi])
    avg = (r + g + b) // 3
    gi_ = min(23, max(0, (avg - 8 + 5) // 10))
    gv = 8 + gi_ * 10
    dc = (r - cube[0]) ** 2 + (g - cube[1]) ** 2 + (b - cube[2]) ** 2
    dg = (r - gv) ** 2 + (g - gv) ** 2 + (b - gv) ** 2
    return 232 + gi_ if dg < dc else 16 + 36 * ri + 6 * gi + bi


def _near16(r, g, b):
    return min(range(16), key=lambda i: (.3 * (r - ANSI16[i][0])) ** 2 + (.59 * (g - ANSI16[i][1])) ** 2 + (.11 * (b - ANSI16[i][2])) ** 2)


class Painter:
    """turns a grid of (top, bottom) colors into escape codes, sending only what changed"""

    def __init__(self, mode="truecolor"):
        self.mode = mode
        self.cache = {}
        self.prev = None
        self.size = None

    def token(self, c):
        """quantize a color for the current color depth (None = transparent)"""
        if c is None:
            return c
        if self.mode == "truecolor":
            return (c[0] & 0xFC, c[1] & 0xFC, c[2] & 0xFC)    # 6 bits are plenty: more cells stay unchanged
        v = self.cache.get(c)
        if v is None:
            v = _near256(*c) if self.mode == "256" else _near16(*c)
            if len(self.cache) > 300000:
                self.cache.clear()
            self.cache[c] = v
        return v

    def sgr(self, fg, bg):
        """escape sequence selecting these (tokenized) colors; None = terminal default"""
        out = ["\x1b[0"]
        if fg is not None:
            out.append(";38;2;%d;%d;%d" % fg if self.mode == "truecolor" else
                       (";38;5;%d" % fg if self.mode == "256" else ";%d" % (30 + fg if fg < 8 else 82 + fg)))
        if bg is not None:
            out.append(";48;2;%d;%d;%d" % bg if self.mode == "truecolor" else
                       (";48;5;%d" % bg if self.mode == "256" else ";%d" % (40 + bg if bg < 8 else 92 + bg)))
        return "".join(out) + "m"

    def cell(self, top, bot):
        """-> (character, fg token, bg token)"""
        if top is None and bot is None:
            return " ", None, None
        if bot is None:
            return "▀", top, None
        if top is None:
            return "▄", bot, None
        return "▀", top, bot

    def encode(self, grid):
        return [[(self.token(t), self.token(b)) for t, b in row] for row in grid]

    def paint(self, grid, status=None, full=False):
        """-> string to write for this frame (diffed against the last one)"""
        enc = self.encode(grid)
        rows, cols = len(enc), len(enc[0]) if enc else 0
        if full or self.prev is None or self.size != (rows, cols):
            self.prev, self.size = [None] * rows, (rows, cols)
        out = ["\x1b[?2026h"]                       # synchronized update (ignored where unsupported)
        state = None
        for ry, row in enumerate(enc):
            prev = self.prev[ry]
            at = -2
            for x, tb in enumerate(row):
                if prev is not None and prev[x] == tb:
                    continue
                if at != x - 1:
                    out.append("\x1b[%d;%dH" % (ry + 1, x + 1))
                ch, fg, bg = self.cell(*tb)
                if state != (fg, bg):
                    out.append(self.sgr(fg, bg))
                    state = (fg, bg)
                out.append(ch)
                at = x
            self.prev[ry] = row
        if status:
            out.append("\x1b[%d;1H\x1b[0;30;47m%s\x1b[0m" % (rows, status[:cols].ljust(cols)))
            self.prev[rows - 1] = None               # repaint that row next frame
        out.append("\x1b[0m\x1b[?2026l")
        return "".join(out)

    def render_lines(self, grid):
        """the grid as plain lines (no cursor movement), for banners printed into the scrollback"""
        lines = []
        for row in self.encode(grid):
            buf, state = [], None
            for tb in row:
                ch, fg, bg = self.cell(*tb)
                if state != (fg, bg):
                    buf.append(self.sgr(fg, bg))
                    state = (fg, bg)
                buf.append(ch)
            buf.append("\x1b[0m")
            lines.append("".join(buf))
        return lines


# ------------------------------------------------------------------- input
_MOUSE = re.compile(r"\x1b\[<(\d+);(\d+);(\d+)([Mm])")
_CSI = re.compile(r"\x1b\[[0-9;?]*([A-Za-z~])")


def parse_input(data):
    """text read from the terminal -> list of events:
    ('key', ch) ('esc',) ('arrow', 'A|B|C|D') ('mouse', button, x, y, pressed)"""
    ev, i, n = [], 0, len(data)
    while i < n:
        ch = data[i]
        if ch == "\x1b":
            if i == n - 1:
                ev.append(("esc",))
                i += 1
                continue
            m = _MOUSE.match(data, i)
            if m:
                ev.append(("mouse", int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4) == "M"))
                i = m.end()
                continue
            m = _CSI.match(data, i)
            if m:
                if m.group(1) in "ABCD" and m.end() - i == 3:
                    ev.append(("arrow", m.group(1)))
                i = m.end()
                continue
            if data[i + 1] == "O" and i + 2 < n:           # application-mode arrows / F-keys
                if data[i + 2] in "ABCD":
                    ev.append(("arrow", data[i + 2]))
                i += 3
                continue
            i += 2                                         # Alt+key: ignore
            continue
        ev.append(("key", ch))
        i += 1
    return ev


def read_events(fd):
    if POSIX:
        data = ""
        while select.select([fd], [], [], 0)[0]:
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            data += chunk.decode(errors="ignore")
        return parse_input(data)
    keys = []
    while msvcrt.kbhit():
        c = msvcrt.getwch()
        if c in ("\x00", "\xe0"):
            msvcrt.getwch()
            continue
        keys.append(("esc",) if c == "\x1b" else ("key", c))
    return keys


class Terminal:
    """alternate screen, hidden cursor, raw-ish input, mouse; everything restored on exit"""

    def __init__(self, mouse=True):
        self.mouse = mouse
        self.keyfd = None
        self.old = None
        self.resized = False
        self.out = sys.stdout

    def size(self):
        import shutil
        s = shutil.get_terminal_size()
        return s.columns, s.lines

    def write(self, text):
        self.out.write(text)
        self.out.flush()

    def __enter__(self):
        if POSIX:
            self.keyfd = sys.stdin.fileno() if sys.stdin.isatty() else os.open("/dev/tty", os.O_RDONLY)
            self.old = termios.tcgetattr(self.keyfd)
            tty.setcbreak(self.keyfd)
            if hasattr(signal, "SIGWINCH"):
                signal.signal(signal.SIGWINCH, lambda *_: setattr(self, "resized", True))
            for sig in (signal.SIGTERM, signal.SIGHUP):
                signal.signal(sig, lambda *_: sys.exit(0))
        self.write("\x1b[?1049h\x1b[?25l\x1b[?7l\x1b[2J" + ("\x1b[?1002h\x1b[?1006h" if self.mouse else ""))
        return self

    def __exit__(self, *exc):
        self.write(("\x1b[?1006l\x1b[?1002l" if self.mouse else "") + "\x1b[0m\x1b[?7h\x1b[?25h\x1b[?1049l")
        if POSIX and self.old is not None:
            termios.tcsetattr(self.keyfd, termios.TCSADRAIN, self.old)
        return False

    def events(self):
        return read_events(self.keyfd)
