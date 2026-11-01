# WeatherLG4000

The 90s Weather Channel look of [WeatherStar 4000+](https://github.com/mwood77/ws4kp-international)
as an app and screen saver for rooted LG webOS TVs. It works for any city in the world:
forecasts come from [Open-Meteo](https://open-meteo.com/), no API key needed.

The app runs straight into kiosk mode with your city, units and display options
baked in, cycles through the forecast screens on its own and refreshes the data
periodically. Optionally it replaces the TV's screen saver: when the TV's screen
saver comes on, WeatherStar starts, and the first key press closes it again.

## Requirements

- An LG webOS TV rooted with [Homebrew Channel](https://github.com/webosbrew/webos-homebrew-channel)
  and SSH enabled in its settings (root access is needed for installing over SSH
  and for the screen saver hook).
- On your computer: `git`, `python3`, `ssh`/`scp` and `rsvg-convert` (librsvg).
  No Node.js or webOS SDK needed.

## Setup

```sh
git clone --recursive https://github.com/Majkenzik/WeatherLG4000.git
cd WeatherLG4000
cp config.example.json config.json   # then edit it
ssh-copy-id root@<tv-ip>             # Homebrew Channel's default password is "alpine"
scripts/deploy.sh install
```

The app shows up on the TV as **WeatherStar 4000+**. Back closes it.

To also use it as the screen saver:

```sh
scripts/deploy.sh screensaver-on     # survives reboots (Homebrew Channel init.d hook)
scripts/deploy.sh screensaver-test   # start the TV's screen saver now to try it
scripts/deploy.sh screensaver-off    # back to LG's screen saver
```

Change `config.json` and run `scripts/deploy.sh install` again to apply it.
`scripts/build.py` alone builds `build/app/` and an `.ipk` you can install any
other way (Homebrew Channel, `ares-install`, webOS Dev Manager).

## config.json

| Key | Meaning |
| --- | --- |
| `location.query` | City name as Open-Meteo's geocoder knows it in English, then a comma and anything (e.g. `"Warsaw, POL"`). |
| `location.lat`, `location.lon` | The city's coordinates. Must be within ~3 km of the geocoder's result for that name. |
| `units.temperature` | `C`, `F` or `K` |
| `units.wind` | `m/s`, `km/h`, `knots`, `mph` or `bft` |
| `units.distance` | `km`, `mi`, `ft` or `meters` |
| `units.pressure` | `hPa`, `inHG` or `mmHG` |
| `units.hours` | `12` or `24` |
| `locale` | Date/time format, e.g. `en-GB` (English, 24-hour) or `pl-PL`. Without it the TV's own locale is used, which for English is 12-hour. |
| `widescreen` | `true` stretches to 16:9 |
| `speed` | `very-fast`, `fast`, `normal`, `slow` or `very-slow` |
| `scanLines` | Retro CRT scan lines |
| `appId` | webOS app id |
| `tv.host`, `tv.user` | Where `deploy.sh` installs to (`TV=<ip> scripts/deploy.sh ...` overrides) |

To find the name and coordinates, search
`https://geocoding-api.open-meteo.com/v1/search?name=<city>&language=en` and take
`latitude`/`longitude` of the right result. The build warns when they don't
match: local names can resolve to the wrong place (`Warszawa` finds a district
in Ohio; `Warsaw` finds Warsaw, Poland).

## How it works

- `vendor/ws4kp-international` is the upstream project as a git submodule,
  pinned to a release. Its prebuilt site in `docs/` is used as-is, minus the
  Webamp music player (an unpinned download that plays music) and the GitHub
  button.
- `scripts/build.py` wraps it in a webOS web app: a launcher page sets your
  location and settings and opens the display in kiosk mode, and `webos/tv.js`
  handles the remote (Back closes; in screen saver mode any key does).
- The screen saver hook (`screensaver/weatherstar-screensaver.sh`) is installed
  into `/var/lib/webosbrew/init.d/`. It watches the TV's power state and, when
  the state turns to *Screen Saver*, closes LG's screen saver (its window sits
  above every app) and launches the app with `{"screensaver": true}`.
  The log is `/tmp/weatherstar-screensaver.log` on the TV.

**OLED owners:** the WeatherStar layout has static parts (logo, clock, bars).
Leaving it on for hours can cause image retention, so don't run it as an
all-day display on an OLED.

## Updating upstream

```sh
cd vendor/ws4kp-international && git fetch --tags && git checkout <new-tag> && cd ../..
scripts/deploy.sh install
```

## Credits

WeatherStar 4000+ by [Matt Walsh (netbymatt)](https://github.com/netbymatt/ws4kp),
international fork by [mwood77](https://github.com/mwood77/ws4kp-international),
based on Mike Battaglia's original. Fonts and icons from
[TWCClassics](https://twcclassics.com/). Weather data by
[Open-Meteo](https://open-meteo.com/) (CC BY 4.0). Screen saver approach
inspired by [webosbrew/custom-screensaver](https://github.com/webosbrew/custom-screensaver).
