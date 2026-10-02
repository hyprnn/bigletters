# bigletters

A random letter, a word, a clock or a countdown fills your **whole terminal**
with colors, effects and animations. Pure Python 3, no dependencies. Needs a
truecolor terminal (most modern ones).

```
python3 bigletter.py        # run it directly
pip install .               # or install it: then just run `bigletters`
```

## Quick tour

```
bigletters                         random letter; Space = next one
bigletters --auto 3                change it by itself every 3 s
bigletters --letters claude        random letters only from c, l, a, u, d, e
bigletters --word "hello world"    show a phrase (long text wraps onto up to 3 lines)
echo "one two three" | bigletters  show words from stdin one by one (or --file words.txt)
bigletters --clock                 big clock          bigletters --countdown 60   timer + fireworks
bigletters --theme fire --font bold --bg stars --deco mirror
bigletters --screensaver           auto mode, any key quits
bigletters --record demo.gif       record the show to an animated GIF
bigletters --list-effects          every effect name
```

## Keys

| Key | Action |
| --- | --- |
| Space / Enter | next letter (or next word from `--file`) |
| any letter, digit or symbol | show it |
| Esc | type your own letter / word / phrase (Enter = show, Esc = cancel) |
| Tab | new random effects |
| Ctrl+L | lock / unlock the current effects |
| Ctrl+T | next color theme |
| Ctrl+F | next font |
| Ctrl+P | pause |
| `+` / `-` | animation speed |
| `?` | help line |
| Ctrl+C | quit |

## Flags

| Flag | Meaning |
| --- | --- |
| `--letters ABC` | random letters come only from these |
| `--word TEXT` | start with this text |
| `--file PATH` | show the words of a file one by one (`-` or a pipe = stdin) |
| `--auto [SECONDS]` | change the text by itself (every 5 s by default) |
| `--theme NAME` | `rainbow` `neon` `fire` `ice` `retro` `mono` `random` |
| `--bg` `--fill` `--geo` `--deco` `--intro` `--font` | lock one effect by name or number (`random` = free) |
| `--speed X` | animation speed |
| `--clock` / `--countdown SECONDS` | clock and timer modes |
| `--screensaver` | auto mode, any key quits |
| `--record FILE.gif` `--record-seconds N` | record to a GIF (default 6 s) |
| `--bell` | beep when the text changes |
| `--time SECONDS` | quit after N seconds |

## Effects

Everything is combined at random and changes every few seconds
(`--list-effects` prints the names):

* **10 backgrounds** - plasma, stripes, digital rain, rings, checkers, stars, spiral, flames, aurora, synthwave grid
* **10 fills** - rainbow, neon, plasma, fire, bands, outline, glitter, chrome, spectrum, strobe
* **10 motions** - breathe, wave, 3D spin, glitch, bounce, zoom, shear, jelly, orbit, fly-in from the distance
* **4 decorations** - none, 3D extrude with rim light, long shadow, water reflection
* **4 intros** - pop, typewriter (with erase), particles that assemble the letter (the old one crumbles), matrix drop
* **6 fonts** - normal, bold, thin, pixel, italic, wavy; letters, digits and common symbols
* **6 themes** - the color palette of every effect
* big terminals are drawn in adaptive blocks, so the animation stays smooth

## Tests

```
python3 -m unittest discover -s tests
```
