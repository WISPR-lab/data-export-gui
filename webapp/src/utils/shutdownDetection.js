import { OPFSManager } from '@/storage/opfs_manager.js'

export function initShutdownDetection(store) {
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
          console.log('[Shutdown] No other tabs detected. Clearing OPFS and localStorage...')
          localStorage.clear()
          const opfsManager = new OPFSManager()
          await opfsManager.nukeAll()
          if (store) {
            store.commit('RESET_STATE')
          }
          console.log('[Shutdown] Cleanup complete')
        } catch (e) {
          console.error('[Shutdown] Error during cleanup:', e)
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
