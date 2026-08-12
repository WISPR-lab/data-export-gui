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

function getSystemLogLevel() {
  var envLevel = process.env.VUE_APP_LOG_LEVEL || 'INFO';
  var upper = String(envLevel).toUpperCase();
  return LOG_LEVELS[upper] !== undefined ? LOG_LEVELS[upper] : LOG_LEVELS.INFO;
}

export function getLogger(name) {
  var prefix = '[' + (name || 'App') + ']';
  var currentLevel = getSystemLogLevel();

  return {
    debug: function () {
      if (currentLevel <= LOG_LEVELS.DEBUG) {
        var args = Array.prototype.slice.call(arguments);
        console.log.apply(console, [prefix, 'DEBUG:'].concat(args));
      }
    },
    info: function () {
      if (currentLevel <= LOG_LEVELS.INFO) {
        var args = Array.prototype.slice.call(arguments);
        console.info.apply(console, [prefix, 'INFO:'].concat(args));
      }
    },
    warn: function () {
      if (currentLevel <= LOG_LEVELS.WARN) {
        var args = Array.prototype.slice.call(arguments);
        console.warn.apply(console, [prefix, 'WARN:'].concat(args));
      }
    },
    error: function () {
      if (currentLevel <= LOG_LEVELS.ERROR) {
        var args = Array.prototype.slice.call(arguments);
        console.error.apply(console, [prefix, 'ERROR:'].concat(args));
      }
    },
  };
}

export default getLogger('App');
