// ponytail: lightweight logger matching python_core logging levels without external deps
// Vue 2 / ES5 compatible (no optional chaining or nullish coalescing)

const LOG_LEVELS = {
  DEBUG: 10,
  INFO: 20,
  WARN: 30,
  WARNING: 30,
  ERROR: 40,
  SILENT: 50,
};

var overrideLogLevel = null;
var showPrefix = true;

function getSystemLogLevel() {
  if (overrideLogLevel !== null) return overrideLogLevel;
  var envLevel = (typeof process !== 'undefined' && process.env && process.env.VUE_APP_LOG_LEVEL) || 'INFO';
  var upper = String(envLevel).toUpperCase();
  return LOG_LEVELS[upper] !== undefined ? LOG_LEVELS[upper] : LOG_LEVELS.INFO;
}

export function setLogLevel(level) {
  var upper = String(level).toUpperCase();
  if (LOG_LEVELS[upper] !== undefined) {
    overrideLogLevel = LOG_LEVELS[upper];
  }
}

export function setShowPrefix(enable) {
  showPrefix = !!enable;
}

export function getLogger(name) {
  var prefix = '[' + (name || 'App') + ']';

  return {
    debug: function () {
      if (getSystemLogLevel() <= LOG_LEVELS.DEBUG) {
        var args = Array.prototype.slice.call(arguments);
        var prefixArgs = showPrefix ? [prefix] : [];
        console.debug.apply(console, prefixArgs.concat(args));
      }
    },
    info: function () {
      if (getSystemLogLevel() <= LOG_LEVELS.INFO) {
        var args = Array.prototype.slice.call(arguments);
        var prefixArgs = showPrefix ? [prefix] : [];
        console.info.apply(console, prefixArgs.concat(args));
      }
    },
    warn: function () {
      if (getSystemLogLevel() <= LOG_LEVELS.WARN) {
        var args = Array.prototype.slice.call(arguments);
        var prefixArgs = showPrefix ? [prefix] : [];
        console.warn.apply(console, prefixArgs.concat(args));
      }
    },
    error: function () {
      if (getSystemLogLevel() <= LOG_LEVELS.ERROR) {
        var args = Array.prototype.slice.call(arguments);
        var prefixArgs = showPrefix ? [prefix] : [];
        console.error.apply(console, prefixArgs.concat(args));
      }
    },
  };
}

export default getLogger('App');
