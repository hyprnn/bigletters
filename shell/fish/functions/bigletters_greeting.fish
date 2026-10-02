# bigletters-managed
# Installed as fish_greeting by `install.sh --greeting`.
# Settings (optional):  set -U bigletters_greeting_text 'my laptop'   set -U bigletters_greeting_rows 5
#                       set -U bigletters_greeting 0   # turn the banner off
function fish_greeting --description 'A big colorful banner when a new shell starts'
    status is-interactive; or return
    command -q bigletters; or return
    set -q bigletters_greeting; and test "$bigletters_greeting" = 0; and return

    set -l text (prompt_hostname)
    set -q bigletters_greeting_text; and set text $bigletters_greeting_text
    set -l rows 5
    set -q bigletters_greeting_rows; and set rows $bigletters_greeting_rows
    bigletters --banner "$text" --rows $rows
end
