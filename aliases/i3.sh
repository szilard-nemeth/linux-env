#!/usr/bin/env bash

if is-platform-macos
then
    echo "$INFO_PREFIX i3 aliases won't be used as platform is $platform!"
    return 1
fi

alias i3-display-unplugged="xrandr --output HDMI1 --off"
alias i3-display-plugged="exec xrandr --output HDMI1 --auto --right-of eDP1"
alias i3-display-primary="xrandr --output HDMI1 --primary"
alias suspend="$HOME/i3/i3exit.sh suspend"