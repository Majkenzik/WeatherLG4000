// Injected into the WeatherStar page when it runs as a webOS app.
// ES5 only: older webOS browsers (Chromium 38 on webOS 3) choke on anything newer.
(function () {
	var KEY_BACK = 461;

	// Upstream formats hours with the browser's default locale, which on a TV
	// set to English is en-US (12-hour) whatever the hours setting says.
	// Default every Intl.DateTimeFormat without an explicit locale to ours.
	var locale = window.WS_LOCALE;
	var NativeDateTimeFormat = Intl.DateTimeFormat;
	if (locale) {
		var DateTimeFormat = function (locales, options) {
			return new NativeDateTimeFormat(locales === undefined ? locale : locales, options);
		};
		DateTimeFormat.prototype = NativeDateTimeFormat.prototype;
		DateTimeFormat.supportedLocalesOf = NativeDateTimeFormat.supportedLocalesOf;
		Intl.DateTimeFormat = DateTimeFormat;
	}

	function launchParams() {
		try {
			return JSON.parse((window.PalmSystem && window.PalmSystem.launchParams) || '{}') || {};
		} catch (e) {
			return {};
		}
	}

	function close() {
		if (window.webOS && window.webOS.platformBack) window.webOS.platformBack();
		window.close();
	}

	// Started by the screensaver hook: behave like a screensaver and get out of
	// the way on the first key press, returning to whatever was on screen.
	function isScreensaver() {
		return launchParams().screensaver === true;
	}

	document.addEventListener('keydown', function (e) {
		if (e.keyCode === KEY_BACK || isScreensaver()) {
			e.preventDefault();
			e.stopPropagation();
			close();
		}
	}, true);

	// Pointer (Magic Remote) movement also dismisses the screensaver.
	var pointerMoves = 0;
	document.addEventListener('mousemove', function () {
		if (isScreensaver() && ++pointerMoves > 3) close();
	}, true);

	// Keep the cursor hidden: it would otherwise sit over the display.
	var style = document.createElement('style');
	style.textContent = '*{cursor:none !important}';
	document.head.appendChild(style);
}());
