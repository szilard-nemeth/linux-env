#!/bin/bash
#MOUNT the given image parameter

#[root@szyszyLAPTOP _SCRIPTS]# sudo ./mount_ISO.sh "/media/Szyszy's Ext_HDD/torrents/diablo_film/Dr House 1.évad/House_1-1.ISO"
#total 4
#dr-xr-xr-x 2 4294967295 4294967295   40 2006-05-31 21:41 AUDIO_TS
#dr-xr-xr-x 2 4294967295 4294967295 1444 2006-05-31 21:41 VIDEO_TS
 

mkdir -p /home/szyszy/mnt/temp_imagedisk
mount -o loop "$1" /home/szyszy/mnt/temp_imagedisk
cd /home/szyszy/mnt/temp_imagedisk/
ls -l

