<template>
  <div class="safe-exit-button">
    <v-tooltip left>
      <template v-slot:activator="{ on, attrs }">
        <v-btn
          fixed
          bottom
          right
          rounded
          color="#d32f2f"
          dark
          v-bind="attrs"
          v-on="on"
          @click="safExit"
          class="mr-4 mb-4"
        >
          Safe Exit
        </v-btn>
      </template>
      <span>Close and wipe all data</span>
    </v-tooltip>
  </div>
</template>

<script>
import BrowserDB from '../database.js'

export default {
  name: 'SafeExitButton',
  methods: {
    async safExit() {
      try {
        console.log('[SafeExit] Initiating safe exit...')
        
        // Wipe all stored data
        await BrowserDB.wipeAllData()
        console.log('[SafeExit] Data wiped')
        
        // Clear browser storage
        localStorage.clear()
        sessionStorage.clear()
        console.log('[SafeExit] Storage cleared')
        
        // Reset in-memory state
        this.$store.commit('RESET_STATE')
        console.log('[SafeExit] Store reset')
        
        // Terminate Pyodide worker if running
        try {
          const worker = new Worker('/pyodideWorker.js')
          worker.terminate()
          console.log('[SafeExit] Worker terminated')
        } catch (e) {
          console.log('[SafeExit] No worker to terminate')
        }
        
        // Clear DOM
        document.body.innerHTML = ''
        
        // Try to close the window
        window.close()
        
        // Fallback if close is blocked - use replace to disable back button
        window.location.replace('https://www.google.com')
      } catch (error) {
        console.error('[SafeExit] Error during safe exit:', error)
        // Force close anyway
        window.close()
      }
    }
  }
}
</script>

<style scoped>
.safe-exit-button {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  z-index: 1000;
}
</style>
