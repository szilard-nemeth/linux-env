#!/usr/bin/env bash

function unmount-poweroff() {
    #sudo umount $1 && udisksctl power-off -b $1
     sudo udisksctl unmount -b $1 && sudo udisksctl power-off -b $1
}