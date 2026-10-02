# bigletters

A random letter, a word, a clock or a countdown fills your **whole terminal** - in a smooth
vector font with neon-tube lighting, animated backgrounds, 3D, reflections and fireworks.
Pure Python 3, no dependencies. Works in any terminal (true color, 256 or 16 colors), and
installs into **fish** with functions, abbreviations and completions.

![demo](docs/demo.gif)

## Install

```sh
git clone https://github.com/hyprnn/bigletters && cd bigletters
./install.sh                # program + fish integration (functions, abbreviations, completions)
./install.sh --greeting     # ...and a big banner whenever a new fish shell starts
```

No root, nothing to compile: the program goes to `~/.local/share/bigletters`, the command to
`~/.local/bin/bigletters`. Remove everything with `./install.sh --uninstall` (your own files, and your
old `fish_greeting`, are never touched or are restored). Other ways to run it:

```sh
python3 bigletter.py        # straight from the checkout
pip install .               # a normal pip install gives the `bigletters` command
```

## Use it

```sh
bigletters                         # random letter; Space or click = next one
bigletters --auto 3                # change it by itself every 3 s
bigletters --demo                  # a tour that shows the name of every effect
bigletters --word "hello world"    # a phrase (wraps onto up to 3 lines)
bigletters --letters claude        # random letters only from c, l, a, u, d, e
echo "one two three" | bigletters  # words from stdin, or --file words.txt
bigletters --clock                 # big clock
bigletters --countdown 90          # timer, fireworks at zero
bigletters --theme fire --font bold --bg stars --deco mirror
bigletters --screensaver           # auto mode, any key quits
bigletters --banner "my laptop"    # a one-off banner printed into the scrollback
bigletters --record demo.gif       # record the show to an animated GIF
bigletters --list-effects          # every effect name
```

### Keys and mouse

| Input | Action |
| --- | --- |
| Space, Enter, `→` | next letter (or next word) |
| `←` | back to the previous text |
| any letter, digit, symbol | show it |
| Esc | type your own letter / word / phrase (Enter = show, Esc = cancel) |
| Tab | new random effects |
| Ctrl+L | lock / unlock the current effects |
| Ctrl+T / Ctrl+F | next color theme / next font |
| Ctrl+P | pause |
| `+` `-` or `↑` `↓` or mouse wheel | animation speed |
| click | next letter and a burst of sparks |
| drag | sparks follow the mouse |
| `?` | help line |
| Ctrl+C | quit |

### Flags

| Flag | Meaning |
| --- | --- |
| `--letters ABC` | random letters come only from these |
| `--word TEXT` / `--file PATH` | start with this text / show the words of a file (`-` or a pipe = stdin) |
| `--auto [SECONDS]` | change the text by itself (every 5 s by default) |
| `--theme NAME` | `rainbow` `neon` `fire` `ice` `retro` `mono` `gold` `sunset` `random` |
| `--bg` `--fill` `--geo` `--deco` `--intro` `--font` | lock one effect by name or number (`random` = free) |
| `--speed X` / `--fps N` | animation speed / frame rate (lower it over a slow ssh) |
| `--clock` / `--countdown SECONDS` | clock and timer modes |
| `--banner [TEXT]` `--rows N` | print a transparent banner into the scrollback and exit |
| `--screensaver` | auto mode, any key or click quits |
| `--record FILE.gif` `--record-seconds N` | record to a GIF (default 6 s) |
| `--colors auto\|truecolor\|256\|16` | color depth (auto-detected; or set `BIGLETTERS_COLORS`) |
| `--info` / `--demo` | show effect names in the status line / a tour with them |
| `--no-mouse` `--bell` `--time SECONDS` | no mouse capture / beep on change / quit after N seconds |

## fish

`./install.sh` puts these into your fish config (`~/.config/fish`):

| | |
| --- | --- |
| `bigdone COMMAND...` | run a command, then a big green **DONE** or red **FAIL** banner and a bell: `bigdone make -j8` |
| `bigsay TEXT...` | print text as a banner: `bigsay -t fire -r 8 build ok` |
| `bigtimer 90` / `5m` / `1h30m` | full-screen countdown with fireworks and a bell |
| `bl`, `blclock`, `blsaver` | abbreviations for `bigletters`, `--clock`, `--screensaver` |
| completions | every flag, every effect and theme name (generated from the real parser) |
| `--greeting` | the banner at shell start, with your hostname. Tune it: `set -U bigletters_greeting_text 'my laptop'`, `set -U bigletters_greeting_rows 5`, off with `set -U bigletters_greeting 0` |

A real screensaver inside tmux: `set -g lock-after-time 300` and `set -g lock-command 'bigletters --screensaver'`.

## What is inside

* **A vector font.** Letters are strokes drawn through a distance field, so edges stay smooth at any
  size and weight (normal, bold, thin, italic, wavy, plus the old 5x7 `pixel` font). Light comes from
  the top left, strokes glow like neon tubes. Letters, digits and common symbols; long text is
  wrapped and squeezed to fit.
* **Effects**, combined at random and cross-faded when they change (`--list-effects`):
  10 backgrounds (plasma, stripes, digital rain, rings, checkers, stars, spiral, flames, aurora,
  synthwave grid), 10 fills, 10 motions (wave, 3D spin, glitch, bounce, jelly, fly-in...),
  4 decorations (3D extrude, long shadow, water reflection), 4 intros (typewriter with erase,
  particles that assemble the letter, matrix drop), 8 color themes.
* **Terminal craft.** Half-block pixels, only changed cells are sent, synchronized updates (no
  tearing), color depth detection with 256 and 16 color fallbacks, resize handling, adaptive quality
  on huge terminals, mouse support, clean restore of your screen on exit.
* **A GIF recorder** with its own encoder - no Pillow, no ffmpeg.

## Develop

```sh
python3 -m unittest discover -s tests        # fonts, effects, painter, GIF, installer, fish functions
python3 tools/gen_fish_completions.py        # regenerate the fish completions after changing flags
python3 tools/make_demo.py                   # re-render docs/demo.gif
```
