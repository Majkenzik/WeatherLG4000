#!/bin/sh
# Build and install WeatherStar 4000+ on a rooted LG webOS TV over SSH.
#
#   scripts/deploy.sh install          build, copy and install the app, then launch it
#   scripts/deploy.sh screensaver-on   start the app whenever the TV's screen saver starts
#   scripts/deploy.sh screensaver-off  undo screensaver-on
#   scripts/deploy.sh screensaver-test trigger the TV's screen saver now
#   scripts/deploy.sh uninstall        remove the app (and the screen saver hook)
#
# The TV address comes from config.json (tv.host), or TV=<address> overrides it.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
CONFIG="$ROOT/config.json"
[ -f "$CONFIG" ] || CONFIG="$ROOT/config.example.json"

config() { python3 -c "import json,sys; c=json.load(open(sys.argv[1])); print($1)" "$CONFIG"; }

APP_ID=$(config "c['appId']")
TV="${TV:-$(config "c['tv']['user'] + '@' + c['tv']['host']")}"
case "$TV" in *@*) ;; *) TV="root@$TV" ;; esac
HOOK=/var/lib/webosbrew/init.d/50-weatherstar-screensaver

# luna-send prints nothing over SSH without a terminal, hence -tt.
on_tv() { ssh -tt -o ConnectTimeout=10 "$TV" "$@" | tr -d '\r'; }

case "${1:-}" in
	install)
		python3 "$ROOT/scripts/build.py"
		IPK=$(ls "$ROOT"/build/*.ipk)
		scp -q "$IPK" "$TV:/tmp/weatherstar.ipk"
		on_tv "luna-send -w 60000 -i luna://com.webos.appInstallService/dev/install \
			'{\"id\":\"$APP_ID\",\"ipkUrl\":\"/tmp/weatherstar.ipk\",\"subscribe\":true}' \
			| grep -m1 -E 'installed|failed|errorText'; rm -f /tmp/weatherstar.ipk"
		on_tv "luna-send -n 1 luna://com.webos.applicationManager/launch '{\"id\":\"$APP_ID\"}'"
		;;
	screensaver-on)
		mkdir -p "$ROOT/build"
		sed "s/__APP_ID__/$APP_ID/" "$ROOT/screensaver/weatherstar-screensaver.sh" > "$ROOT/build/screensaver-hook.sh"
		on_tv "mkdir -p /var/lib/webosbrew/init.d"
		scp -q "$ROOT/build/screensaver-hook.sh" "$TV:$HOOK"
		# Plain ssh, no -tt: closing a terminal would hang up the watcher.
		ssh "$TV" "chmod 755 $HOOK && $HOOK"
		echo "Screen saver hook installed and started."
		;;
	screensaver-off)
		on_tv "rm -f $HOOK; pkill -f '[5]0-weatherstar-screensaver --daemon'; pkill -f '[g]etPowerState.*subscribe'; true"
		echo "Screen saver hook removed."
		;;
	screensaver-test)
		on_tv "luna-send -n 1 luna://com.webos.service.tvpower/power/turnOnScreenSaver '{}'"
		;;
	uninstall)
		on_tv "rm -f $HOOK; pkill -f '[5]0-weatherstar-screensaver --daemon'; luna-send -w 30000 -i luna://com.webos.appInstallService/dev/remove \
			'{\"id\":\"$APP_ID\",\"subscribe\":true}' | grep -m1 -E 'removed|failed|errorText'"
		;;
	*)
		sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
		exit 1
		;;
esac
