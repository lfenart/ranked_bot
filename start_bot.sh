#!/bin/sh
nohup python3 Bot/main.py > bot.log &
echo $! > bot_pid.txt
