#!/bin/bash
sudo /usr/local/miniconda/bin/python3.7 -m pip install catkin_pkg crcmod crc16

python3.7 modules/drivers/radar/umrr_radar/python/crt_scripts/crt_objects_umrr_can_publisher.py modules/drivers/radar/umrr_radar/python/crt_conf/umrr_radar_for_objects_front_left_conf.json
