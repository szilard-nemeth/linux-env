#!/usr/bin/env bash

if [[ $platform == 'macOS' ]]; then
    echo "$INFO_PREFIX i3 aliases won't be used as platform is $platform!"
    return 1
fi
function i3-rename-window() {
  xdotool set_window --name "$1" `xdotool getactivewindow`
}

function i3-rename-workspace() {
  i3-input -F 'rename workspace to "%s"' -P 'New name: ' 2>&1 > /dev/null
}

alias i3-display-unplugged="xrandr --output HDMI1 --off"
alias i3-display-plugged="exec xrandr --output HDMI1 --auto --right-of eDP1"
alias i3-display-primary="xrandr --output HDMI1 --primary"
alias suspend="$HOME/i3/i3exit.sh suspend"