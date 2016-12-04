#!/bin/bash
## Simple shell script that reboots the bot if it crashes

#prefix="[$(date +"%Y-%m-%d %H:%M:%S")] "

echo "[$(date +"%Y-%m-%d %H:%M:%S")] Running bot."
until python redditbot.py; do
	echo "[$(date +"%Y-%m-%d %H:%M:%S")] CRASH" >&2
	sleep 1
done
