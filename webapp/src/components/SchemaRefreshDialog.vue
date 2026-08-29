<!-- Added for anonymous-research-group/data-export-gui 
 
Shown when a SQL query fails with "no such table/column" -->
<template>
  <v-dialog :value="value" @input="$emit('input', $event)" max-width="500px" persistent :z-index="25000">
    <v-card>
      <v-card-title class="headline">
        Local Database Out of Date
        <v-spacer></v-spacer>
        <v-btn icon small @click="close"><v-icon>mdi-close</v-icon></v-btn>
      </v-card-title>

      <v-card-text>
        <p class="mb-3">
          Your there is leftover cached data that doesn't match the current database schema
          (likely left over from an older version of the app).
        </p>
        <p class="mb-3">
          Please click <strong>Reset &amp; Reload</strong> below to clear local data and start fresh.
        </p>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="error" text :loading="resetting" @click="resetAndReload">Reset &amp; Reload</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { resetAllLocalData } from '@/database/index.js'
import { getLogger } from '@/utils/logger'

const logger = getLogger('SchemaRefreshDialog')

export default {
  name: 'SchemaRefreshDialog',
  props: {
    value: {
      type: Boolean,
      default: false
    }
  },
  data: function() {
    return {
      resetting: false
    }
  },
  methods: {
    close: function() {
      this.$emit('input', false)
    },
    resetAndReload: async function() {
      if (this.resetting) return
      this.resetting = true
      try {
        await resetAllLocalData({ unregisterServiceWorkers: true })
      } catch (e) {
        logger.error('Error resetting local data:', e)
      }
      window.location.reload()
    }
  }
}
</script>
