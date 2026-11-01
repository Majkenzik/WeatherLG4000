#!/bin/sh
# Shows WeatherStar 4000+ whenever the TV starts its screen saver.
#
# Installed into /var/lib/webosbrew/init.d/, which the Homebrew Channel runs
# at boot. It follows tvpower's power state and, when the screen saver comes
# on, launches the app with {"screensaver":true}; the app then closes itself
# on the first key press. After MINUTES of screen saver it closes the app and
# turns the screen off, to spare OLED panels a static picture for hours.

APP_ID="__APP_ID__"
MINUTES=__MINUTES__
LOG=/tmp/weatherstar-screensaver.log
TIMER=/tmp/weatherstar-screensaver.timer

foreground_is_app() {
	luna-send -n 1 luna://com.webos.applicationManager/getForegroundAppInfo '{}' 2>/dev/null |
		grep -q "\"appId\":\"$APP_ID\""
}

# LG's screen saver comes back every few minutes over the app too, so a timer
# already running for this session is kept rather than restarted.
start_timer() {
	[ "$MINUTES" -gt 0 ] || return
	if [ "$1" = keep ] && [ -f "$TIMER" ] && kill -0 "$(cat "$TIMER")" 2>/dev/null; then
		return
	fi
	[ -f "$TIMER" ] && kill "$(cat "$TIMER")" 2>/dev/null
	(
		sleep $((MINUTES * 60))
		if foreground_is_app; then
			echo "$(date) $MINUTES min up, closing $APP_ID and turning the screen off" >>"$LOG"
			luna-send -n 1 luna://com.webos.applicationManager/closeByAppId "{\"id\":\"$APP_ID\"}" >>"$LOG" 2>&1
			luna-send -n 1 luna://com.webos.service.tvpower/power/turnOffScreen '{}' >>"$LOG" 2>&1
		fi
		rm -f "$TIMER"
	) &
	echo $! >"$TIMER"
}

watch() {
	# -n with a huge count rather than -i: -i quits at once when stdin is not a terminal.
	luna-send -n 1000000000 luna://com.webos.service.tvpower/power/getPowerState '{"subscribe":true}' </dev/null 2>>"$LOG" |
	while read -r line; do
		case "$line" in
			*'"state":"Screen Saver"'*|*'"state": "Screen Saver"'*)
				echo "$(date) screen saver on, launching $APP_ID" >>"$LOG"
				# Already showing us: same session, keep its timer.
				if foreground_is_app; then start_timer keep; else start_timer new; fi
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
