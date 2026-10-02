#!/usr/bin/env python3
"""Render docs/demo.gif without a terminal: a scripted tour of letters, words and themes.
    python3 tools/make_demo.py [out.gif]"""
import os
import random
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from bigletters import fx  # noqa: E402
from bigletters.gif import Recorder  # noqa: E402
from bigletters.show import Show  # noqa: E402

COLS, ROWS, FPS = 80, 22, 30
# (time, text, theme, locks) - what happens when
SCENES = [
    (0.0, "B", "rainbow", dict(bg=0, fill=0, geo=0, deco=1, intro=0)),
    (2.0, "I", "neon", dict(bg=5, fill=1, geo=2, deco=0, intro=2)),
    (4.0, "G", "fire", dict(bg=7, fill=3, geo=4, deco=2, intro=0)),
    (6.0, "FISH", "ice", dict(bg=8, fill=7, geo=0, deco=3, intro=1)),
    (8.5, "42", "retro", dict(bg=9, fill=6, geo=1, deco=0, intro=3)),
]
END = 11.0


def main(path):
    random.seed(7)
    rec = Recorder(path, END, scale=3, every=2, delay_cs=7)
    show = None
    t, dt, i = 0.0, 1 / FPS, 0
    while t < END:
        if i < len(SCENES) and t >= SCENES[i][0]:
            _, text, theme, locks = SCENES[i]
            fx.set_theme(theme)
            if show is None:
                show = Show(COLS, ROWS, text=text, locks=locks)
            else:
                show.locks = locks
                show.apply_locks()
                show.new_effects(t)
                show.apply_locks()
                show.change(text, t)
            i += 1
        show.step(dt, t)
        rec.add(show.frame(t), t)
        t += dt
    rec.save()
    print("wrote", path, "(%d frames)" % len(rec.frames))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "demo.gif"))
