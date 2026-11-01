#!/bin/sh
# Shows WeatherStar 4000+ whenever the TV starts its screen saver.
#
# Installed into /var/lib/webosbrew/init.d/, which the Homebrew Channel runs
# at boot. It follows tvpower's power state and, when the screen saver comes
# on, launches the app with {"screensaver":true}; the app then closes itself
# on the first key press.

APP_ID="__APP_ID__"
LOG=/tmp/weatherstar-screensaver.log

watch() {
	# -n with a huge count rather than -i: -i quits at once when stdin is not a terminal.
	luna-send -n 1000000000 luna://com.webos.service.tvpower/power/getPowerState '{"subscribe":true}' </dev/null 2>>"$LOG" |
	while read -r line; do
		case "$line" in
			*'"state":"Screen Saver"'*|*'"state": "Screen Saver"'*)
				echo "$(date) screen saver on, launching $APP_ID" >>"$LOG"
				# LG's screen saver window sits above every app, so close it
				# first; launching while it is up leaves the app hidden under it.
				luna-send -n 1 luna://com.webos.applicationManager/closeByAppId \
					'{"id":"com.webos.app.screensaver"}' >>"$LOG" 2>&1
				sleep 1
				luna-send -n 1 luna://com.webos.applicationManager/launch \
					"{\"id\":\"$APP_ID\",\"params\":{\"screensaver\":true}}" >>"$LOG" 2>&1
				;;
		esac
	done
}

if [ "${1:-}" = "--daemon" ]; then
	# luna-send exits if tvpower restarts; resubscribe.
	while true; do
		watch
		sleep 5
	done
fi

# Detach into a new session so the watcher outlives the shell (or SSH
# session) that started it, and never run two.
pkill -f "$0 --daemon" 2>/dev/null
setsid -f "$0" --daemon </dev/null >/dev/null 2>&1
