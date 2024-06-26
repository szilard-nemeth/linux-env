#!/usr/bin/env bash

if is-platform-macos
then
    print_debug "$INFO_PREFIX i3 functions won't be used as platform is $platform!"
    return 1
fi

function i3-rename-window {
  xdotool set_window --name "$1" `xdotool getactivewindow`
}

function i3-rename-workspace {
  i3-input -F 'rename workspace to "%s"' -P 'New name: ' 2>&1 > /dev/null
}