# bigletters-managed (installed by bigletters/install.sh; remove with: install.sh --uninstall)
# Puts the bigletters command on PATH and adds a few short abbreviations.

if not contains -- "@BIN@" $PATH
    set -gx PATH "@BIN@" $PATH
end

if status is-interactive
    abbr --add bl bigletters
    abbr --add blclock 'bigletters --clock'
    abbr --add blsaver 'bigletters --screensaver'
end
