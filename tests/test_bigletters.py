import io, os, random, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from bigletters import cli, font as F, fx, gif, term
from bigletters.show import Show


def lzw_decode(data, min_bits=8):
    """reference GIF LZW decoder, to check our encoder"""
    clear, eoi = 1 << min_bits, (1 << min_bits) + 1
    bits = int.from_bytes(data, "little")
    total = len(data) * 8
    pos, size = 0, min_bits + 1
    table, out, prev = {}, bytearray(), None

    def reset():
        nonlocal table, size, prev
        table = {i: bytes((i,)) for i in range(clear)}
        table[clear] = table[eoi] = b""
        size, prev = min_bits + 1, None
    reset()
    while pos + size <= total:
        code = (bits >> pos) & ((1 << size) - 1)
        pos += size
        if code == clear:
            reset()
            continue
        if code == eoi:
            break
        if prev is None:
            entry = table[code]
        elif code in table:
            entry = table[code]
            table[len(table)] = table[prev] + entry[:1]
        else:
            entry = table[prev] + table[prev][:1]
            table[len(table)] = entry
        out += entry
        prev = code
        if len(table) == (1 << size) and size < 12:
            size += 1
    return bytes(out)


class Fonts(unittest.TestCase):
    def test_every_char_has_both_fonts(self):
        self.assertEqual(set(F.STROKES), set(F.BITS))
        for ch, rows in F.BITS.items():
            self.assertEqual(len(rows), 7)
            self.assertTrue(all(len(r) == 5 for r in rows))

    def test_stroke_glyphs_draw_something(self):
        for ch in F.STROKES:
            m = F.build_masks(ch, 40, 56)
            self.assertGreater(sum(1 for v in m["alpha"] if v > .5), 8, ch)
            self.assertTrue(all(0 <= v <= 1 for v in m["alpha"]))
            self.assertTrue(all(0 <= v <= 1 for v in m["core"]))

    def test_all_styles(self):
        for style in F.FONT_NAMES:
            m = F.build_masks("Hi 42!".upper(), 80, 30, style)
            self.assertGreater(sum(1 for v in m["alpha"] if v > .5), 50, style)

    def test_clean(self):
        self.assertEqual(F.clean("  hello   World! ~ é "), "HELLO WORLD!")
        self.assertEqual(F.clean("~~~"), "")

    def test_layout_wraps_long_phrase(self):
        s1, lines1, *_ = F.layout("HELLO", 120, 80)
        self.assertEqual(lines1, ["HELLO"])
        s2, lines2, *_ = F.layout("ONE TWO THREE FOUR", 120, 80)
        self.assertTrue(1 < len(lines2) <= 3)
        self.assertEqual(" ".join(lines2), "ONE TWO THREE FOUR")

    def test_single_letter_fills_height(self):
        s, lines, stretch, uw, uh = F.layout("A", 120, 80)
        self.assertAlmostEqual(s * uh, .9 * 80, places=3)

    def test_long_text_is_squeezed_not_tiny(self):
        s, lines, stretch, *_ = F.layout("12:34:56", 120, 80)
        self.assertLess(stretch, 1.7)
        self.assertGreater(s, 3)

    def test_blank(self):
        F.build_masks("", 40, 20)
        F.build_masks("   ", 40, 20)

    def test_letter_stays_inside_canvas(self):
        for text in ("W", "MMMMMM", "I", "WIDE LOAD OK"):
            m = F.build_masks(text, 90, 30)
            x0, y0, x1, y1 = m["box"]
            self.assertGreaterEqual(x0, 0); self.assertGreaterEqual(y0, 0)
            self.assertLessEqual(x1, 90); self.assertLessEqual(y1, 30)


class Shows(unittest.TestCase):
    def render(self, text="R", font=0, **locks):
        random.seed(1)
        s = Show(40, 12, text=text, locks=locks, font=font)
        s.flash = 0
        for t in (0.1, 0.6, 1.4, 2.6):
            grid = s.frame(t)
            self.assertEqual((len(grid), len(grid[0])), (12, 40))
            for row in grid:
                for cell in row:
                    for c in cell:
                        self.assertTrue(all(isinstance(v, int) and 0 <= v <= 255 for v in c), c)
            s.step(.1, t)
        return s

    def test_every_axis_value(self):
        for axis, n in fx.AXIS_SIZE.items():
            for i in range(n):
                self.render(**{axis: i})

    def test_combination_sample(self):
        random.seed(5)
        for _ in range(40):
            self.render(**{a: random.randrange(n) for a, n in fx.AXIS_SIZE.items()})

    def test_fonts_and_text(self):
        for f in range(len(F.FONT_NAMES)):
            self.render(font=f, text="HI 42!")

    def test_themes(self):
        for name in fx.THEME_NAMES:
            fx.set_theme(name)
            self.render(bg=0, fill=0)
        fx.set_theme("rainbow")

    def test_effect_crossfade(self):
        random.seed(2)
        s = Show(40, 12, text="R")
        s.flash = 0
        s.new_effects(1.0)
        for t in (1.0, 1.3, 1.6, 2.5):
            s.frame(t)

    def test_quality_blocks(self):
        for q in (1, 2, 3, 4):
            s = Show(40, 12, text="R")
            s.q = q
            self.assertEqual(len(s.frame(1.0)), 12)

    def test_transparent_banner_frame(self):
        s = Show(40, 6, text="HI", locks={"deco": 0, "geo": 0, "intro": 0}, transparent=True)
        s.flash, s.born, s.parts = 0, -100, []
        grid = s.frame(3.0)
        flat = [c for row in grid for cell in row for c in cell]
        self.assertIn(None, flat)
        self.assertTrue(any(c is not None for c in flat))

    def test_typewriter_outro_and_change(self):
        random.seed(3)
        s = Show(40, 12, text="A", locks={"intro": 1})
        s.change("B", 2.0)
        self.assertEqual(s.text, "A")
        s.step(.1, 2.6)
        self.assertEqual(s.text, "B")

    def test_locks_and_pool_and_words(self):
        s = Show(30, 10, text="A", locks={"bg": 3, "fill": 2})
        for _ in range(20):
            s.new_effects()
            self.assertEqual((s.bg, s.fill), (3, 2))
        s.all_locked = True
        geo = s.geo
        s.new_effects()
        self.assertEqual(s.geo, geo)
        w = Show(30, 10, words=["ONE", "TWO"], text=None)
        self.assertEqual((w.text, w.next_text(), w.next_text()), ("ONE", "TWO", "ONE"))
        p = Show(30, 10, pool=list("CLAUDE"))
        for _ in range(30):
            self.assertIn(p.next_text(), "CLAUDE")


class Terminal(unittest.TestCase):
    def test_detect_colors(self):
        self.assertEqual(term.detect_colors({"COLORTERM": "truecolor"}), "truecolor")
        self.assertEqual(term.detect_colors({"TERM": "xterm-256color"}), "256")
        self.assertEqual(term.detect_colors({"TERM": "linux"}), "16")
        self.assertEqual(term.detect_colors({"TERM": "xterm-kitty"}), "truecolor")
        self.assertEqual(term.detect_colors({"TERM": "xterm", "BIGLETTERS_COLORS": "16"}), "16")

    def test_quantizers(self):
        self.assertEqual(term._near256(0, 0, 0), 16)
        self.assertEqual(term._near256(255, 255, 255), 231)
        self.assertEqual(term._near256(128, 128, 128) // 100, 2)         # a gray ramp entry
        self.assertEqual(term._near16(250, 5, 5), 9)
        self.assertEqual(term._near16(0, 0, 0), 0)

    def test_parse_input(self):
        ev = term.parse_input("a\x1b[C\x1b[<0;12;7M\x1b[<0;12;7m\x1b[<64;1;1M\x1bOA\x1b[3~z")
        self.assertEqual(ev, [("key", "a"), ("arrow", "C"), ("mouse", 0, 12, 7, True), ("mouse", 0, 12, 7, False),
                              ("mouse", 64, 1, 1, True), ("arrow", "A"), ("key", "z")])
        self.assertEqual(term.parse_input("\x1b"), [("esc",)])
        self.assertEqual(term.parse_input("\x1bx"), [])                  # Alt+x is ignored

    def test_painter_diff(self):
        for mode in ("truecolor", "256", "16"):
            p = term.Painter(mode)
            red, blue = (250, 10, 10), (10, 10, 250)
            grid = [[(red, blue), (red, red)], [(None, None), (blue, None)]]
            first = p.paint(grid)
            self.assertIn("▀", first)
            self.assertIn("▄" if False else "▀", first)
            again = p.paint(grid)
            self.assertNotIn("▀", again)                            # nothing changed -> nothing drawn
            grid[0][1] = (blue, blue)
            third = p.paint(grid)
            self.assertEqual(third.count("▀"), 1)
            self.assertIn("\x1b[1;2H", third)

    def test_painter_status_and_lines(self):
        p = term.Painter("truecolor")
        out = p.paint([[((1, 2, 3), (4, 5, 6))] * 5] * 2, status="hello")
        self.assertIn("hello", out)
        lines = p.render_lines([[((9, 9, 9), None), (None, (8, 8, 8)), (None, None)]])
        self.assertEqual(len(lines), 1)
        self.assertIn("▀", lines[0]); self.assertIn("▄", lines[0])


def emulate(out, screen, mode):
    """apply painter output to a virtual screen: dict (row, col) -> (char, fg, bg), 0-based"""
    import re
    row = col = 0
    fg = bg = None
    pos = 0
    pat = re.compile(r"\x1b\[(\?2026[hl])|\x1b\[(\d+);(\d+)H|\x1b\[([0-9;]*)m|(.)", re.S)
    for m in pat.finditer(out):
        if m.group(1):
            continue
        if m.group(2):
            row, col = int(m.group(2)) - 1, int(m.group(3)) - 1
        elif m.group(4) is not None:
            codes = [int(c) for c in m.group(4).split(";") if c != ""] or [0]
            fg = bg = None
            i = 1 if codes[0] == 0 else 0
            while i < len(codes):
                c = codes[i]
                if c == 38 and codes[i + 1] == 2:
                    fg = tuple(codes[i + 2:i + 5]); i += 5
                elif c == 48 and codes[i + 1] == 2:
                    bg = tuple(codes[i + 2:i + 5]); i += 5
                elif c in (38, 48):
                    if c == 38: fg = codes[i + 2]
                    else: bg = codes[i + 2]
                    i += 3
                else:
                    if 30 <= c <= 37: fg = c - 30
                    elif 90 <= c <= 97: fg = c - 82
                    elif 40 <= c <= 47: bg = c - 40
                    elif 100 <= c <= 107: bg = c - 92
                    i += 1
        else:
            screen[(row, col)] = (m.group(5), fg, bg)
            col += 1


class PainterDiff(unittest.TestCase):
    def test_diffed_frames_rebuild_the_exact_screen(self):
        for mode in ("truecolor", "256", "16"):
            random.seed(11)
            show = Show(30, 8, text="K")
            show.flash = 0
            p = term.Painter(mode)
            screen = {}
            for i in range(6):
                grid = show.frame(1.0 + i * .13)
                if i == 3:
                    grid[2][5] = (None, (9, 9, 9))               # transparent cells too
                    grid[3][6] = (None, None)
                emulate(p.paint(grid), screen, mode)
                want = p.encode(grid)
                for y, row in enumerate(want):
                    for x, (top, bot) in enumerate(row):
                        ch, fg, bg = p.cell(top, bot)
                        self.assertEqual(screen[(y, x)], (ch, fg, bg), (mode, i, y, x))


class Gif(unittest.TestCase):
    def test_lzw_roundtrip(self):
        rnd = random.Random(7)
        for data in (b"", b"\x05", bytes(1000), bytes(rnd.randrange(256) for _ in range(5000)),
                     bytes((i // 30) % 7 for i in range(60000))):
            self.assertEqual(lzw_decode(gif.lzw_encode(data)), data)

    def test_recorder_writes_valid_gif(self):
        random.seed(4)
        s = Show(20, 6, text="G")
        rec = gif.Recorder(os.path.join(tempfile.mkdtemp(), "x.gif"), 5)
        for i in range(6):
            rec.add(s.frame(i * .1), i * .1)
        path = rec.save()
        with open(path, "rb") as f:
            data = f.read()
        self.assertTrue(data.startswith(b"GIF89a") and data.endswith(b"\x3b"))
        self.assertEqual(rec.size, (40, 24))
        self.assertEqual(len(rec.frames), 3)


class Cli(unittest.TestCase):
    def test_resolve(self):
        self.assertEqual(cli.resolve(fx.BG_NAMES, "plasma", "bg"), 0)
        self.assertEqual(cli.resolve(fx.BG_NAMES, "3", "bg"), 3)
        self.assertIsNone(cli.resolve(fx.BG_NAMES, "random", "bg"))
        with self.assertRaises(SystemExit):
            cli.resolve(fx.BG_NAMES, "nope", "bg")

    def test_countdown_format(self):
        self.assertEqual(cli.fmt_countdown(59.2), "01:00")
        self.assertEqual(cli.fmt_countdown(0), "00:00")
        self.assertEqual(cli.fmt_countdown(3725), "1:02:05")

    def test_list_effects(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main(["--list-effects"])
        self.assertIn("plasma", buf.getvalue())
        self.assertIn("gold", buf.getvalue())

    def test_banner(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main(["--banner", "fish", "--rows", "5", "--colors", "256", "--theme", "fire"])
        lines = buf.getvalue().rstrip("\n").split("\n")
        self.assertEqual(len(lines), 5)
        self.assertIn("38;5;", buf.getvalue())

    def test_parser(self):
        a = cli.build_parser().parse_args(["--auto", "--letters", "claude", "--theme", "fire", "--bg", "stars"])
        self.assertEqual((a.auto, a.letters), (cli.AUTO_SECS, "claude"))

    def test_launcher_runs(self):
        out = subprocess.run([sys.executable, os.path.join(ROOT, "bigletter.py"), "--version"], capture_output=True, text=True)
        self.assertIn("bigletters", out.stdout)
        out = subprocess.run([sys.executable, "-m", "bigletters", "--list-effects"], capture_output=True, text=True, cwd=ROOT)
        self.assertIn("rainbow", out.stdout)


class Install(unittest.TestCase):
    """the installer and the fish integration, in a throw-away HOME"""

    def run_install(self, home, *args):
        env = dict(os.environ, HOME=home, XDG_DATA_HOME="", XDG_CONFIG_HOME="")
        return subprocess.run(["sh", os.path.join(ROOT, "install.sh"), *args], env=env, capture_output=True, text=True)

    def test_install_and_uninstall(self):
        home = tempfile.mkdtemp()
        r = self.run_install(home, "--fish", "--greeting")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        cmd = os.path.join(home, ".local", "bin", "bigletters")
        self.assertTrue(os.access(cmd, os.X_OK))
        out = subprocess.run([cmd, "--version"], capture_output=True, text=True, env=dict(os.environ, HOME=home))
        self.assertIn("bigletters", out.stdout)
        fish = os.path.join(home, ".config", "fish")
        for rel in ("conf.d/bigletters.fish", "functions/bigsay.fish", "functions/bigdone.fish", "functions/bigtimer.fish",
                    "functions/__bigtimer_seconds.fish", "functions/fish_greeting.fish", "completions/bigletters.fish"):
            self.assertTrue(os.path.isfile(os.path.join(fish, rel)), rel)
        with open(os.path.join(fish, "conf.d", "bigletters.fish")) as f:
            self.assertIn(os.path.join(home, ".local", "bin"), f.read())           # @BIN@ was substituted
        r = self.run_install(home, "--uninstall")
        self.assertEqual(r.returncode, 0, r.stderr)
        left = [os.path.join(d, n) for d, _, names in os.walk(home) for n in names]
        self.assertEqual(left, [], left)

    def test_user_greeting_is_kept_and_restored(self):
        home = tempfile.mkdtemp()
        funcs = os.path.join(home, ".config", "fish", "functions")
        os.makedirs(funcs)
        mine = os.path.join(funcs, "fish_greeting.fish")
        with open(mine, "w") as f:
            f.write("function fish_greeting; echo mine; end\n")
        self.assertEqual(self.run_install(home, "--greeting").returncode, 0)
        self.assertEqual(self.run_install(home, "--greeting").returncode, 0)          # twice: still fine
        self.run_install(home, "--uninstall")
        with open(mine) as f:
            self.assertIn("echo mine", f.read())

    def test_foreign_files_are_not_touched(self):
        home = tempfile.mkdtemp()
        comp = os.path.join(home, ".config", "fish", "completions")
        os.makedirs(comp)
        theirs = os.path.join(comp, "bigsay.fish")
        with open(theirs, "w") as f:
            f.write("# my own completion\n")
        self.run_install(home, "--fish")
        self.run_install(home, "--uninstall")
        with open(theirs) as f:
            self.assertEqual(f.read(), "# my own completion\n")

    def test_completions_are_up_to_date(self):
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import gen_fish_completions
        with open(os.path.join(ROOT, "shell", "fish", "completions", "bigletters.fish")) as f:
            self.assertEqual(f.read(), gen_fish_completions.generate(), "run: python3 tools/gen_fish_completions.py")

    @unittest.skipUnless(subprocess.run(["sh", "-c", "command -v fish"], capture_output=True).returncode == 0, "fish is not installed")
    def test_fish_files_have_valid_syntax(self):
        for d, _, names in os.walk(os.path.join(ROOT, "shell", "fish")):
            for n in names:
                r = subprocess.run(["fish", "-n", os.path.join(d, n)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, n + r.stderr)

    @unittest.skipUnless(subprocess.run(["sh", "-c", "command -v fish"], capture_output=True).returncode == 0, "fish is not installed")
    def test_fish_functions_work(self):
        home = tempfile.mkdtemp()
        self.assertEqual(self.run_install(home, "--fish").returncode, 0)
        env = dict(os.environ, HOME=home, TERM="xterm-256color")
        script = ("for d in 90 5m 1h30m 2m15s; echo (__bigtimer_seconds $d); end; "
                  "bigsay hi; bigdone true; echo status=$status; bigdone false; echo status=$status")
        r = subprocess.run(["fish", "-c", script], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith("90\n300\n5400\n135\n"), r.stdout[:40])
        self.assertIn("status=0", r.stdout)
        self.assertIn("status=1", r.stdout)
        self.assertIn("\u2580", r.stdout)


if __name__ == "__main__":
    unittest.main()
