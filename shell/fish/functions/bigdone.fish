# bigletters-managed
function bigdone --description 'Run a command, then show a big DONE or FAIL banner'
    if test (count $argv) -eq 0
        echo "usage: bigdone COMMAND [ARGS...]    e.g.  bigdone make -j8" >&2
        return 2
    end

    set -l started (date +%s)
    $argv
    set -l code $status
    set -l took (math (date +%s) - $started)

    if test $code -eq 0
        bigletters --banner DONE --rows 6 --theme neon
    else
        bigletters --banner FAIL --rows 6 --theme fire
    end
    printf '\a'
    set_color brblack
    echo "  $argv[1] finished in "$took"s with status $code"
    set_color normal
    return $code
end
