import { resetAllLocalData } from '@/database/index.js'
import { getLogger } from '@/utils/logger';

const logger = getLogger('Shutdown');

const LAST_ACTIVE_KEY = 'lastActiveTimestamp';
const INACTIVITY_THRESHOLD_MS = 3 * 60 * 60 * 1000; // 3 hours

export function initShutdownDetection(store) {
  /* Pings other tabs via BroadcastChannel; nukes local data if no tab responds within 500ms (cold start only, skipped on refresh). */
  const shutdownChannel = new BroadcastChannel('shutdown-detection')

  // Always respond to pings from other tabs
  shutdownChannel.addEventListener('message', (event) => {
    if (event.data === 'ping') {
      shutdownChannel.postMessage('ping-response')
    }
  })

  if (!sessionStorage.getItem('isRefresh')) {
    let responseReceived = false   // ping other tabs to see if any are running
    const timeout = setTimeout(async () => {
      if (!responseReceived) {
        try {
          logger.debug('No other tabs detected. Clearing local data...')
          await resetAllLocalData()
          if (store) {
            store.commit('RESET_STATE')
          }
          logger.debug('Cleanup complete')
        } catch (e) {
          logger.error('Error during cleanup:', e)
        }
      }
    }, 500)

    shutdownChannel.postMessage('ping')

    const responseHandler = (event) => {
      if (event.data === 'ping-response') {
        responseReceived = true
        clearTimeout(timeout)
        shutdownChannel.removeEventListener('message', responseHandler)
      }
    }
    shutdownChannel.addEventListener('message', responseHandler)
  }

  sessionStorage.setItem('isRefresh', 'true')
}

export function initInactivityDetection(store) {
  /* Threat model: data left in OPFS/localStorage on a shared or borrowed machine
     shouldn't survive an extended period where nobody touched the tab. Tracks a
     last-active timestamp in localStorage (updated on click/keydown/scroll,
     throttled) and wipes local data if more than INACTIVITY_THRESHOLD_MS has
     passed since. Checked on load and on visibilitychange rather than a running
     timer, since background-tab timers are throttled/suspended by the browser -
     exactly when a long idle period would occur. Silent: no confirmation prompt,
     no post-wipe dialog: just reloads so no stale data is left rendered. */
  const recordActivity = () => {
    localStorage.setItem(LAST_ACTIVE_KEY, String(Date.now()));
  };

  const checkInactivity = async () => {
    const last = parseInt(localStorage.getItem(LAST_ACTIVE_KEY), 10);
    if (last && Date.now() - last > INACTIVITY_THRESHOLD_MS) {
      try {
        logger.debug('Inactivity threshold exceeded. Wiping local data...')
        await resetAllLocalData()
        if (store) {
          store.commit('RESET_STATE')
        }
        window.location.reload()
        return
      } catch (e) {
        logger.error('Error during inactivity wipe:', e)
      }
    }
    recordActivity();
  };

  checkInactivity();

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      checkInactivity();
    }
  });

  // Throttled so scroll/keydown spam doesn't hammer localStorage.
  let throttled = false;
  const onActivity = () => {
    if (throttled) return;
    throttled = true;
    setTimeout(() => { throttled = false; }, 60000);
    recordActivity();
  };
  ['click', 'keydown', 'scroll'].forEach((evt) => {
    document.addEventListener(evt, onActivity, { passive: true });
  });
}
