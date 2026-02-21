<!-- SAFE EXIT BUTTON -->

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
          @click="safeExit"
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
import { terminatePyodideWorker } from '@/pyodide/pyodide-client.js'
import { OPFSManager } from '@/storage/opfs_manager';   

export default {
  name: 'SafeExitButton',
  methods: {
    async safeExit() {
      try {
        console.log('[SafeExit] Initiating safe exit...')
        
        terminatePyodideWorker();
        const opfsManager = new OPFSManager();
        await opfsManager.nukeAll();
        console.log('[SafeExit] Storage cleared')
        
        this.$store.commit('RESET_STATE')
        console.log('[SafeExit] Store reset')
        
        document.body.innerHTML = ''

        window.close()
        window.location.replace('https://www.google.com')
      } catch (error) {
        console.error('[SafeExit] Error during safe exit:', error)
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
