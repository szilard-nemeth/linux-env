#!/bin/bash
############################################################
#
############################################################
function lock {
    i3lock -c 000000
}
case "$1" in
    lock)
        lock
        ;;
    logout)
        i3-msg exit
        ;;
    suspend)
        #lock && systemctl suspend
        lock && sudo pm-suspend
        ;;
    reboot)
        #systemctl reboot
        systemctl sudo reboot
        ;;
    poweroff)
        #systemctl poweroff
        systemctl sudo shutdown
        ;;
    *)
        echo "Usage: $0 {lock|logout|suspend|reboot|poweroff}"
        exit 2
esac

exit 0
