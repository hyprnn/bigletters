# bigletters-managed
function bigtimer --description 'Big full-screen countdown: bigtimer 90 | 5m | 1h30m'
    if test (count $argv) -eq 0
        echo "usage: bigtimer DURATION    e.g.  bigtimer 90   bigtimer 5m   bigtimer 1h30m" >&2
        return 2
    end
    set -l secs (__bigtimer_seconds $argv[1])
    or begin
        echo "bigtimer: cannot read '$argv[1]' (try 90, 5m, 1h30m)" >&2
        return 2
    end
    bigletters --countdown $secs $argv[2..-1]
    printf '\a'
end
