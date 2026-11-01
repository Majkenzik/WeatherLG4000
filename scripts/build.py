#!/usr/bin/env python3
"""Build the webOS app (build/app) and its .ipk (build/*.ipk) from config.json.

Uses only the Python standard library and the prebuilt site that
ws4kp-international ships in its docs/ folder, so no node toolchain is needed.
"""
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / 'vendor' / 'ws4kp-international'
BUILD = ROOT / 'build'
APP = BUILD / 'app'
VERSION = '1.0.0'

# Option values of the selects in upstream server/scripts/modules/settings.mjs.
UNIT_OPTIONS = {
	'temperature': ('temperatureUnits', {'C': 1, 'F': 2, 'K': 3}),
	'wind': ('windUnits', {'m/s': 1, 'km/h': 2, 'knots': 3, 'mph': 4, 'bft': 5}),
	'distance': ('distanceUnits', {'km': 1, 'mi': 2, 'ft': 3, 'meters': 4}),
	'pressure': ('pressureUnits', {'hPa': 1, 'inHG': 2, 'mmHG': 3}),
	'hours': ('hoursFormat', {'12': 1, '24': 2}),
}
SPEEDS = {'very-fast': 0.5, 'fast': 0.75, 'normal': 1.0, 'slow': 1.25, 'very-slow': 1.5}


def load_config():
	path = ROOT / 'config.json'
	if not path.exists():
		path = ROOT / 'config.example.json'
		print(f'config.json not found, using {path.name}')
	return json.loads(path.read_text())


def query_string(config):
	location = config['location']
	params = {
		'latLonQuery': location['query'],
		'latLon': json.dumps({'lat': location['lat'], 'lon': location['lon']}, separators=(',', ':')),
		'kiosk': 'true',
		'settings-wide-checkbox': str(bool(config.get('widescreen', True))).lower(),
		'settings-scanLines-checkbox': str(bool(config.get('scanLines', False))).lower(),
		'settings-hideWebamp-checkbox': 'true',
		'settings-speed-select': SPEEDS[config.get('speed', 'normal')],
	}
	for display, enabled in config.get('displays', {}).items():
		params[f'{display}-checkbox'] = str(bool(enabled)).lower()
	for key, value in config.get('units', {}).items():
		setting, options = UNIT_OPTIONS[key]
		if str(value) not in options:
			sys.exit(f'units.{key}: "{value}" is not one of {", ".join(options)}')
		params[f'settings-{setting}-select'] = options[str(value)]
	return urlencode(params)


def check_location(location):
	"""Warn when Open-Meteo's geocoder won't find the configured place.

	Upstream looks the city up by the part of `query` before the first comma and
	keeps the result within 0.03 degrees of lat/lon; with no match it falls back
	to the first result (for "Warszawa" that is a district in Ohio).
	"""
	name = location['query'].split(',')[0]
	url = 'https://geocoding-api.open-meteo.com/v1/search?' + urlencode(
		{'name': name, 'count': 100, 'language': 'en', 'format': 'json'})
	try:
		with urllib.request.urlopen(url, timeout=10) as response:
			results = json.load(response).get('results', [])
	except OSError as error:
		print(f'Skipping location check ({error})')
		return
	if not any(abs(r['latitude'] - location['lat']) < 0.03 and abs(r['longitude'] - location['lon']) < 0.03
			for r in results):
		print(f'WARNING: geocoding "{name}" finds nothing near {location["lat"]}, {location["lon"]}. '
			'Use the English name Open-Meteo knows (e.g. "Warsaw", not "Warszawa") and its coordinates.')


def patch_index(html, locale):
	# Webamp is pulled unpinned from unpkg and plays music: heavy for a TV and
	# unwanted in a screensaver. The GitHub star button is useless in kiosk mode.
	html, count = re.subn(r'<script type="module">\s*import Webamp.*?</script>', '', html, flags=re.S)
	if count != 1:
		sys.exit('Could not find the Webamp script in upstream index.html; check the upstream version.')
	html = re.sub(r'<script[^>]*buttons\.github\.io[^>]*></script>', '', html)
	# tv.js must run before the upstream bundle so its Intl override is in place.
	head = f'<head><script>window.WS_LOCALE={json.dumps(locale)};</script><script src="tv.js"></script>'
	return html.replace('<head>', head, 1)


def write_app(config):
	shutil.rmtree(BUILD, ignore_errors=True)
	shutil.copytree(UPSTREAM / 'docs', APP / 'www')
	index = APP / 'www' / 'index.html'
	index.write_text(patch_index(index.read_text(), config.get("locale")))
	shutil.copy(ROOT / 'webos' / 'tv.js', APP / 'www' / 'tv.js')

	# Upstream only picks the geocoding result matching our coordinates when
	# they are already in localStorage; from a bare permalink it takes the first
	# result, which can be a same-named place on another continent.
	location = config['location']
	target = 'www/index.html?' + query_string(config)
	(APP / 'index.html').write_text(
		'<!DOCTYPE html><html><head><meta charset="utf-8"><title>WeatherStar 4000+</title>'
		'<style>html,body{margin:0;background:#000}</style><script>'
		f'localStorage.setItem("latLonQuery",{json.dumps(location["query"])});'
		f'localStorage.setItem("latLon",{json.dumps(json.dumps({"lat": location["lat"], "lon": location["lon"]}))});'
		'localStorage.removeItem("latLonFromGPS");'
		f'location.replace({json.dumps(target)});'
		'</script></head><body></body></html>\n')

	for size, name in ((80, 'icon.png'), (130, 'largeIcon.png')):
		subprocess.run(['rsvg-convert', '-w', str(size), '-h', str(size), '--keep-aspect-ratio',
			str(ROOT / 'assets' / 'icon.svg'), '-o', str(APP / name)], check=True)

	appinfo = {
		'id': config['appId'],
		'version': VERSION,
		'vendor': 'WeatherLG4000',
		'type': 'web',
		'main': 'index.html',
		'title': 'WeatherStar 4000+',
		'icon': 'icon.png',
		'largeIcon': 'largeIcon.png',
		'resolution': '1920x1080',
		'disableBackHistoryAPI': True,
	}
	(APP / 'appinfo.json').write_text(json.dumps(appinfo, indent='\t') + '\n')
	return appinfo


def tar_bytes(add):
	buffer = io.BytesIO()
	with tarfile.open(fileobj=buffer, mode='w:gz', format=tarfile.GNU_FORMAT) as tar:
		add(tar)
	return buffer.getvalue()


def add_bytes(tar, name, data, mode=0o644):
	info = tarfile.TarInfo(name)
	info.size = len(data)
	info.mode = mode
	info.mtime = int(time.time())
	tar.addfile(info, io.BytesIO(data))


def as_root(info):
	info.uid = info.gid = 0
	info.uname = info.gname = 'root'
	return info


def write_ipk(appinfo):
	app_id = appinfo['id']
	installed_size = sum(f.stat().st_size for f in APP.rglob('*') if f.is_file())
	control = (
		f'Package: {app_id}\nVersion: {appinfo["version"]}\nSection: misc\nPriority: optional\n'
		f'Architecture: all\nInstalled-Size: {installed_size}\nMaintainer: WeatherLG4000\n'
		f'Description: {appinfo["title"]}\nwebOS-Package-Format-Version: 2\n'
		f'webOS-Packager-Version: x.y.x\n')
	control_tar = tar_bytes(lambda tar: add_bytes(tar, './control', control.encode()))

	def add_data(tar):
		prefix = f'./usr/palm/applications/{app_id}'
		tar.add(APP, arcname=prefix, filter=as_root)
		add_bytes(tar, f'./usr/palm/packages/{app_id}/packageinfo.json', json.dumps({
			'app': app_id, 'id': app_id, 'loc_name': appinfo['title'], 'version': appinfo['version'],
		}).encode())
	data_tar = tar_bytes(add_data)

	# An .ipk is a Debian-style `ar` archive.
	ipk = BUILD / f'{app_id}_{appinfo["version"]}_all.ipk'
	with open(ipk, 'wb') as out:
		out.write(b'!<arch>\n')
		for name, data in ((b'debian-binary', b'2.0\n'), (b'control.tar.gz', control_tar), (b'data.tar.gz', data_tar)):
			header = b'%-16s%-12d%-6d%-6d%-8s%-10d`\n' % (name + b'/', int(time.time()), 0, 0, b'100644', len(data))
			out.write(header + data + (b'\n' if len(data) % 2 else b''))
	return ipk


def main():
	if not (UPSTREAM / 'docs' / 'index.html').exists():
		sys.exit('Upstream missing: run `git submodule update --init` first.')
	config = load_config()
	check_location(config["location"])
	appinfo = write_app(config)
	ipk = write_ipk(appinfo)
	print(f'Built {APP.relative_to(ROOT)}/ and {ipk.relative_to(ROOT)}')


if __name__ == '__main__':
	main()
