import itertools, os, random, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import bigletter as B


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


class Glyphs(unittest.TestCase):
    def test_shape(self):
        for ch, rows in B.BITS.items():
            self.assertEqual(len(rows), 7, ch)
            self.assertTrue(all(len(r) == 5 for r in rows), ch)

    def test_all_letters_and_digits(self):
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
            self.assertIn(ch, B.BITS)
            self.assertTrue(any(any(r) for r in B.BITS[ch]), ch)

    def test_clean(self):
        self.assertEqual(B.clean("  hello   World! ~ é "), "HELLO WORLD!")
        self.assertEqual(B.clean("~~~"), "")


class Layout(unittest.TestCase):
    def test_wraps_long_phrase(self):
        s1, lines1, _ = B.layout("HELLO", 120, 80)
        self.assertEqual(lines1, ["HELLO"])
        s2, lines2, _ = B.layout("ONE TWO THREE FOUR", 120, 80)
        self.assertGreater(len(lines2), 1)
        self.assertLessEqual(len(lines2), 3)
        self.assertEqual(" ".join(lines2), "ONE TWO THREE FOUR")

    def test_single_letter_fills(self):
        s, lines, st = B.layout("A", 120, 80)
        self.assertAlmostEqual(s, .9 * 80 / 7, places=3)

    def test_long_text_is_squeezed_not_tiny(self):
        s, lines, st = B.layout("12:34:56", 120, 80)
        self.assertLess(st, 1.7)
        self.assertGreater(s, 3)

    def test_blank(self):
        B.layout("", 40, 20)


class Effects(unittest.TestCase):
    def render(self, **kw):
        random.seed(1)
        s = B.Show(40, 12, text=kw.pop("text", "R"), locks={k: kw[k] for k in ("bg", "fill", "geo", "deco", "intro") if k in kw},
                   font=kw.get("font", 0))
        s.flash = 0
        out = []
        for t in (0.1, 0.6, 1.4, 2.6):
            grid = s.frame(t)
            self.assertEqual(len(grid), 12)
            self.assertEqual(len(grid[0]), 40)
            for row in grid:
                for cell in row:
                    for c in cell:
                        self.assertTrue(all(isinstance(v, int) and 0 <= v <= 255 for v in c), c)
            s.step(.1, t)
            out.append(grid)
        return out

    def test_every_axis_value(self):
        for axis, n in B.AXIS_SIZE.items():
            for i in range(n):
                self.render(**{axis: i})

    def test_combinations_sample(self):
        random.seed(5)
        for _ in range(40):
            self.render(bg=random.randrange(B.N_BG), fill=random.randrange(B.N_FILL), geo=random.randrange(B.N_GEO),
                        deco=random.randrange(B.N_DECO), intro=random.randrange(B.N_INTRO))

    def test_fonts_and_text(self):
        for f in range(len(B.FONT_NAMES)):
            self.render(font=f, text="HI 42!")

    def test_themes(self):
        for name in B.THEME_NAMES:
            B.set_theme(name)
            self.render(bg=0, fill=0)
        B.set_theme("rainbow")

    def test_letter_visible(self):
        random.seed(2)
        s = B.Show(60, 20, text="O", locks={"intro": 0})
        self.assertGreater(sum(1 for v in s.mask if v > .5), 100)

    def test_typewriter_outro_and_change(self):
        random.seed(3)
        s = B.Show(40, 12, text="A", locks={"intro": 1})
        s.change("B", 2.0)                      # starts erasing
        self.assertEqual(s.text, "A")
        s.step(.1, 2.6)
        self.assertEqual(s.text, "B")

    def test_new_effects_respects_locks(self):
        s = B.Show(30, 10, text="A", locks={"bg": 3, "fill": 2})
        for _ in range(20):
            s.new_effects()
            self.assertEqual((s.bg, s.fill), (3, 2))
        s.all_locked = True
        geo = s.geo
        s.new_effects()
        self.assertEqual(s.geo, geo)

    def test_words_cycle(self):
        s = B.Show(30, 10, words=["ONE", "TWO"], text=None)
        self.assertEqual(s.text, "ONE")
        self.assertEqual(s.next_text(), "TWO")
        self.assertEqual(s.next_text(), "ONE")

    def test_letters_pool(self):
        s = B.Show(30, 10, pool=list("CLAUDE"))
        for _ in range(30):
            self.assertIn(s.next_text(), "CLAUDE")

    def test_quality_blocks(self):
        s = B.Show(40, 12, text="R")
        s.q = 3
        self.assertEqual(len(s.frame(1.0)), 12)


class Gif(unittest.TestCase):
    def test_lzw_roundtrip(self):
        rnd = random.Random(7)
        for data in (b"", b"\x05", bytes(1000), bytes(rnd.randrange(256) for _ in range(5000)),
                     bytes((i // 30) % 7 for i in range(60000))):
            self.assertEqual(lzw_decode(B.lzw_encode(data)), data)

    def test_recorder_writes_valid_gif(self):
        random.seed(4)
        s = B.Show(20, 6, text="G")
        rec = B.Recorder(os.path.join(tempfile.mkdtemp(), "x.gif"), 5)
        for i in range(6):
            rec.add(s.frame(i * .1), i * .1)
        path = rec.save()
        with open(path, "rb") as f:
            data = f.read()
        self.assertTrue(data.startswith(b"GIF89a"))
        self.assertTrue(data.endswith(b"\x3b"))
        self.assertEqual(rec.size, (40, 24))
        self.assertEqual(len(rec.frames), 3)


class Cli(unittest.TestCase):
    def test_resolve(self):
        self.assertEqual(B.resolve(B.BG_NAMES, "plasma", "bg"), 0)
        self.assertEqual(B.resolve(B.BG_NAMES, "3", "bg"), 3)
        self.assertIsNone(B.resolve(B.BG_NAMES, "random", "bg"))
        with self.assertRaises(SystemExit):
            B.resolve(B.BG_NAMES, "nope", "bg")

    def test_countdown_format(self):
        self.assertEqual(B.fmt_countdown(59.2), "01:00")
        self.assertEqual(B.fmt_countdown(0), "00:00")
        self.assertEqual(B.fmt_countdown(3725), "1:02:05")

    def test_list_effects(self):
        B.main(["--list-effects"])

    def test_parser(self):
        a = B.build_parser().parse_args(["--auto", "--letters", "claude", "--theme", "fire", "--bg", "stars"])
        self.assertEqual(a.auto, B.AUTO_SECS)
        self.assertEqual(a.letters, "claude")


if __name__ == "__main__":
    unittest.main()
