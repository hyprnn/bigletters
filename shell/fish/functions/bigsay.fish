# bigletters-managed
function bigsay --description 'Print text as a big colorful banner'
    argparse 'r/rows=' 't/theme=' 'f/font=' h/help -- $argv
    or return 2

    if set -q _flag_help; or test (count $argv) -eq 0
        echo "usage: bigsay [-r ROWS] [-t THEME] [-f FONT] TEXT..."
        echo "       bigsay hello world"
        echo "       bigsay -t fire -r 8 BUILD OK"
        return 0
    end

    set -l args --banner (string join ' ' -- $argv)
    set -q _flag_rows; and set args $args --rows $_flag_rows
    set -q _flag_theme; and set args $args --theme $_flag_theme
    set -q _flag_font; and set args $args --font $_flag_font
    bigletters $args
end
