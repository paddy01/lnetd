#!/bin/bash

sudo rm /etc/telegraf/telegraf.d/*.conf
cd /opt/lnetd/telegraf.d/
sudo python3.7 generate_telegraf_config.py

sudo service telegraf reload > /dev/null
