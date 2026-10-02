# bigletters

A random English letter (or a word) fills your whole terminal, with colors,
effects and animations. Pure Python 3, no dependencies. Needs a truecolor
terminal.

```
python3 bigletter.py
```

| Key | Action |
| --- | --- |
| Space / Enter | new random letter |
| any letter | show that letter |
| Tab | switch effects |
| Esc | type your own letter or word (Enter = show, Esc = cancel) |
| Ctrl+C | quit |

| Flag | Meaning |
| --- | --- |
| `--letters claude` | random letters come only from c, l, a, u, d, e |
| `--word claude` | start by showing this word |
| `--auto [SECONDS]` | change the letter by itself (every 5 s by default) |
| `--time SECONDS` | quit after N seconds |

10 backgrounds, 10 letter fills and 9 motion effects are combined at random
and change every few seconds.
