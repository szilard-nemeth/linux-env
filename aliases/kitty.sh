alias kitty-copy-screen="kitty @ get-text --extent screen | kitty +kitten clipboard"
alias kitty-copy-last-command="kitty @ get-text --extent last_cmd_output | kitty +kitten clipboard"
alias kitty-copy-all="kitty @ get-text --extent all | kitty +kitten clipboard"
# alias kitty-shortcuts='/Applications/kitty.app/Contents/MacOS/kitty --debug-config 2>&1 | grep -E "^(map|mouse_map) " | sort | less'

kitty-shortcuts() {
  local conf="${KITTY_CONFIG_DIRECTORY:-$HOME/.config/kitty}/kitty.conf"
  [[ -f $conf ]] || { echo "no kitty.conf at $conf" >&2; return 1; }
  # Follow `include` lines one level deep, then grep map/mouse_map
  {
    print -- "# $conf"
    grep -E '^(map|mouse_map) ' "$conf"
    grep -E '^include ' "$conf" | awk '{print $2}' | while read -r inc; do
      [[ $inc = /* ]] || inc="$(dirname "$conf")/$inc"
      [[ -f $inc ]] || continue
      print -- "\n# $inc"
      grep -E '^(map|mouse_map) ' "$inc"
    done
  } | less
}
