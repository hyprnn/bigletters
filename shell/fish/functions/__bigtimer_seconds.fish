# bigletters-managed
function __bigtimer_seconds --description 'Turn 90, 5m, 1h30m, 2m15s into seconds'
    set -l m (string match -r '^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?$' -- $argv[1])
    or return 1
    set -l h 0
    set -l mi 0
    set -l s 0
    # unmatched groups may be missing or empty depending on the fish version
    set -l parts (string match -r '(\d+)([hms]?)' -a -- $argv[1])
    set -l i 2
    while test $i -le (count $parts)
        set -l n $parts[$i]
        set -l unit $parts[(math $i + 1)]
        switch "$unit"
            case h
                set h $n
            case m
                set mi $n
            case '*'
                set s $n
        end
        set i (math $i + 3)
    end
    math "$h * 3600 + $mi * 60 + $s"
end
