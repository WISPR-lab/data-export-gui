<!-- SAFE EXIT BUTTON -->
<!-- Added for wispr-lab/data-export-gui -->
<template>
  <div v-if="!demoMode" class="safe-exit-button">
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
          :loading="exiting"
          :disabled="exiting"
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
import { resetAllLocalData } from '@/database/index.js'
import EventBus from '@/event-bus.js'
import { getLogger } from '@/utils/logger';

const logger = getLogger('SafeExit');

export default {
  name: 'SafeExitButton',
  data: function() {
    return {
      exiting: false // race condition guard to prevent multiple clicks
    }
  },
  computed: {
    demoMode() {
      return this.$store.state.demoMode
    }
  },
  methods: {
    async safeExit() {
      if (this.exiting) return
      this.exiting = true
      logger.debug('Initiating safe exit...')

      let dataFullyCleared = true
      try {
        await resetAllLocalData({ unregisterServiceWorkers: true })
      } catch (error) {
        dataFullyCleared = false
        logger.error('Error during safe exit — local data may not be fully cleared:', error)
        EventBus.$emit('opfsUnavailable')
      }
      try {
        this.$store.commit('RESET_STATE')
        document.body.innerHTML = ''
      } catch (error) {
        logger.error('Error clearing app state during safe exit:', error)
      }
      if (!dataFullyCleared) {
        window.alert(
          'Some local data may not have been fully cleared. Please close this browser tab/window manually to be safe.'
        )
      }
      try {
        window.close()
      } catch (error) {
        logger.error('window.close() failed:', error)
      }
      window.location.replace('https://www.google.com')
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
