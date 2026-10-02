#!/bin/sh
# bigletters installer - installs the program and the fish shell integration.
#
#   ./install.sh                  install (program + fish functions, abbreviations, completions)
#   ./install.sh --greeting       also show a big banner whenever a new fish shell starts
#   ./install.sh --uninstall      remove everything this script installed
#
# Options:  --prefix DIR   where the program lives     (default ~/.local/share/bigletters)
#           --bin DIR      where the command goes      (default ~/.local/bin)
#           --pip          install with `pip install --user` instead of copying files
#           --no-fish      skip the fish integration     --fish   install it even if fish is missing
#           -h, --help
#
# Nothing needs root. Everything installed is marked "bigletters-managed", so --uninstall
# never touches files that are not ours (an existing fish_greeting is backed up and restored).
set -eu

REPO_URL="${BIGLETTERS_REPO:-https://github.com/hyprnn/bigletters}"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
PREFIX="$DATA_HOME/bigletters"
BIN_DIR="$HOME/.local/bin"
FISH_DIR="$CONFIG_HOME/fish"
MARK="bigletters-managed"

ACTION=install
GREETING=0
USE_PIP=0
FISH_MODE=auto

if [ -t 1 ]; then
    B=$(printf '\033[1m'); G=$(printf '\033[32m'); Y=$(printf '\033[33m'); R=$(printf '\033[31m'); N=$(printf '\033[0m')
else
    B=''; G=''; Y=''; R=''; N=''
fi
say()  { printf '%s\n' "$*"; }
ok()   { printf '%s\n' "${G}✓${N} $*"; }
warn() { printf '%s\n' "${Y}!${N} $*" >&2; }
die()  { printf '%s\n' "${R}error:${N} $*" >&2; exit 1; }

usage() { sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
    case "$1" in
        --uninstall) ACTION=uninstall ;;
        --greeting) GREETING=1 ;;
        --no-greeting) GREETING=0 ;;
        --pip) USE_PIP=1 ;;
        --no-fish) FISH_MODE=no ;;
        --fish) FISH_MODE=yes ;;
        --prefix) [ $# -ge 2 ] || die "--prefix needs a directory"; PREFIX="$2"; shift ;;
        --bin) [ $# -ge 2 ] || die "--bin needs a directory"; BIN_DIR="$2"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown option: $1 (try --help)" ;;
    esac
    shift
done

is_ours() { [ -f "$1" ] && grep -q "$MARK" "$1" 2>/dev/null; }

fish_wanted() {
    case "$FISH_MODE" in
        yes) return 0 ;;
        no) return 1 ;;
        *) command -v fish >/dev/null 2>&1 || [ -d "$FISH_DIR" ] ;;
    esac
}

# ------------------------------------------------------------------ uninstall
if [ "$ACTION" = uninstall ]; then
    removed=0
    rm_ours() { if is_ours "$1"; then rm -f "$1"; removed=$((removed + 1)); fi; }
    rm_ours "$BIN_DIR/bigletters"
    if [ -d "$PREFIX/lib/bigletters" ] && [ -f "$PREFIX/.$MARK" ]; then rm -rf "$PREFIX"; removed=$((removed + 1)); fi
    for f in "$FISH_DIR"/conf.d/*.fish "$FISH_DIR"/functions/*.fish "$FISH_DIR"/completions/*.fish; do
        [ "$(basename "$f")" = fish_greeting.fish ] && continue
        rm_ours "$f"
    done
    if is_ours "$FISH_DIR/functions/fish_greeting.fish"; then
        rm -f "$FISH_DIR/functions/fish_greeting.fish"; removed=$((removed + 1))
        if [ -f "$FISH_DIR/functions/fish_greeting.fish.bak-bigletters" ]; then
            mv "$FISH_DIR/functions/fish_greeting.fish.bak-bigletters" "$FISH_DIR/functions/fish_greeting.fish"
            ok "restored your previous fish_greeting"
        fi
    fi
    if command -v pip3 >/dev/null 2>&1 && pip3 show bigletters >/dev/null 2>&1; then
        pip3 uninstall -y bigletters >/dev/null 2>&1 && removed=$((removed + 1)) || warn "could not remove the pip package"
    fi
    ok "uninstalled ($removed items removed). Open a new fish shell to drop the abbreviations."
    exit 0
fi

# -------------------------------------------------------------------- install
PYTHON=""
for p in python3 python; do
    if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys; sys.exit(sys.version_info < (3, 8))' 2>/dev/null; then
        PYTHON=$(command -v "$p"); break
    fi
done
[ -n "$PYTHON" ] || die "Python 3.8 or newer is required (install python3 and run again)"

# where are the sources? next to this script, or fetched from git when run through a pipe
SRC=$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)
TMP=""
if [ ! -d "$SRC/bigletters" ]; then
    command -v git >/dev/null 2>&1 || die "no sources next to the script and git is missing"
    TMP=$(mktemp -d)
    trap 'rm -rf "$TMP"' EXIT
    say "fetching $REPO_URL ..."
    git clone --depth 1 -q "$REPO_URL" "$TMP/src" || die "could not clone $REPO_URL"
    SRC="$TMP/src"
fi

say "${B}Installing bigletters${N}"

if [ "$USE_PIP" = 1 ]; then
    "$PYTHON" -m pip install --user --upgrade "$SRC" || die "pip install failed (try without --pip)"
    ok "installed with pip (command: bigletters)"
else
    mkdir -p "$PREFIX/lib" "$BIN_DIR"
    rm -rf "$PREFIX/lib/bigletters"
    cp -R "$SRC/bigletters" "$PREFIX/lib/bigletters"
    find "$PREFIX/lib/bigletters" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
    : > "$PREFIX/.$MARK"
    cat > "$BIN_DIR/bigletters" <<EOF
#!/bin/sh
# $MARK
exec env PYTHONPATH="$PREFIX/lib\${PYTHONPATH:+:\$PYTHONPATH}" "$PYTHON" -m bigletters "\$@"
EOF
    chmod +x "$BIN_DIR/bigletters"
    ok "program   -> $PREFIX/lib/bigletters"
    ok "command   -> $BIN_DIR/bigletters"
fi

# does the new command work?
if [ "$USE_PIP" = 0 ]; then
    "$BIN_DIR/bigletters" --version >/dev/null 2>&1 || die "the installed command does not run: $BIN_DIR/bigletters --version"
fi

# ----------------------------------------------------------------------- fish
if fish_wanted; then
    mkdir -p "$FISH_DIR/conf.d" "$FISH_DIR/functions" "$FISH_DIR/completions"
    for dir in conf.d functions completions; do
        for f in "$SRC"/shell/fish/$dir/*.fish; do
            name=$(basename "$f")
            [ "$name" = bigletters_greeting.fish ] && continue
            dest="$FISH_DIR/$dir/$name"
            if [ -f "$dest" ] && ! is_ours "$dest"; then
                warn "keeping your existing $dest (not ours)"; continue
            fi
            sed "s|@BIN@|$BIN_DIR|g" "$f" > "$dest"
        done
    done
    ok "fish      -> $FISH_DIR  (functions: bigsay, bigdone, bigtimer; abbr: bl, blclock, blsaver; completions)"

    if [ "$GREETING" = 1 ]; then
        dest="$FISH_DIR/functions/fish_greeting.fish"
        if [ -f "$dest" ] && ! is_ours "$dest"; then
            cp "$dest" "$dest.bak-bigletters"
            warn "your fish_greeting was backed up to $dest.bak-bigletters"
        fi
        sed "s|@BIN@|$BIN_DIR|g" "$SRC/shell/fish/functions/bigletters_greeting.fish" > "$dest"
        ok "greeting  -> a banner is shown when a new fish shell starts (turn off: set -U bigletters_greeting 0)"
    fi

    if command -v fish >/dev/null 2>&1; then
        for f in "$FISH_DIR"/conf.d/bigletters.fish "$FISH_DIR"/functions/big*.fish "$FISH_DIR"/completions/big*.fish; do
            [ -f "$f" ] || continue
            fish -n "$f" 2>/dev/null || warn "fish reports a syntax problem in $f"
        done
        if PATH="$BIN_DIR:$PATH" fish -c 'bigletters --version >/dev/null; and functions -q bigsay' 2>/dev/null; then
            ok "fish can run bigletters"
        else
            warn "fish could not run bigletters - open a new shell and try: bigletters --version"
        fi
    else
        warn "fish is not installed here; the files are in place for when it is"
    fi
else
    say "fish not found - skipping the fish integration (use --fish to install it anyway)"
fi

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) warn "$BIN_DIR is not on your PATH yet (fish gets it automatically; for other shells add it)" ;;
esac

say ""
say "${B}Try it:${N}  bigletters      bigletters --auto      bigsay hello      bigdone sleep 2      bigtimer 25m"
say "Remove it any time with:  $0 --uninstall"
