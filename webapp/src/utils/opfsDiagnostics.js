// custom to WISPR-lab/data-export-gui

/**
 * Diagnoses why window.crossOriginIsolated is false.
 * Returns a short cause label plus raw state fields for display.
 * @returns {Promise<{cause: string, sabAvailable: boolean, swSupported: boolean, swRegistered: boolean, swControlling: boolean}>}
 */
export async function diagnoseOpfsFailure() {
  var sabAvailable = typeof SharedArrayBuffer !== 'undefined';
  var swSupported = 'serviceWorker' in navigator;
  var swRegistered = false;
  var swControlling = false;
  var cause;

  if (!window.isSecureContext) {
    cause = 'Page not served over HTTPS';
    return { cause, sabAvailable, swSupported, swRegistered, swControlling };
  }

  if (!swSupported) {
    cause = 'Browser does not support service workers';
    return { cause, sabAvailable, swSupported, swRegistered, swControlling };
  }

  var regs = [];
  try {
    regs = await navigator.serviceWorker.getRegistrations();
  } catch (e) {
    cause = 'Service worker API unavailable';
    return { cause, sabAvailable, swSupported, swRegistered, swControlling };
  }

  for (var i = 0; i < regs.length; i++) {
    var scriptURL = (regs[i].active && regs[i].active.scriptURL) || '';
    if (scriptURL.indexOf('coi-serviceworker') !== -1) {
      swRegistered = true;
      break;
    }
  }

  if (!swRegistered) {
    cause = 'Security service worker not registered';
    return { cause, sabAvailable, swSupported, swRegistered, swControlling };
  }

  swControlling = !!navigator.serviceWorker.controller;

  if (!swControlling) {
    cause = 'Service worker registered but not yet controlling the page';
    return { cause, sabAvailable, swSupported, swRegistered, swControlling };
  }

  // SW is active and controlling — browser isn't honouring the injected headers
  if (!sabAvailable) {
    // Browser is blocking SharedArrayBuffer regardless of headers — known behaviour in Safari/Firefox private mode
    cause = 'Browser is blocking SharedArrayBuffer (private browsing mode prevents this regardless of headers)';
  } else {
    cause = 'Service worker active but cross-origin isolation not granted by browser';
  }
  return { cause, sabAvailable, swSupported, swRegistered, swControlling };
}
