<template>
  <v-app>
    <v-container fill-height class="d-flex align-center justify-center">
      <div class="text-center">
        <h1 class="mb-4">Timeline Analyzer</h1>
        <p class="text-h6 mb-8 text-muted">Local-first forensic timeline tool</p>
        
        <v-btn
          large
          color="primary"
          @click="goToExplore"
          :loading="loading"
        >
          Start Analyzing
        </v-btn>
        
        <div class="mt-8 text-caption text-muted">
          <p>Import data files to begin analyzing timelines</p>
        </div>
      </div>
    </v-container>
  </v-app>
</template>

<script>
import BrowserDB from '../database.js'

export default {
  name: 'HomeNew',
  data() {
    return {
      loading: false,
    }
  },
  mounted() {
    // Initialize default sketch if it doesn't exist
    this.ensureDefaultSketch()
  },
  methods: {
    async ensureDefaultSketch() {
      try {
        // Check if default sketch (ID 1) exists
        const response = await BrowserDB.getSketch(1)
        if (response.data.objects[0]) {
          // Default sketch exists, we can proceed
          return
        }
      } catch (e) {
        // Sketch doesn't exist, create it
      }
      
      // Create default sketch
      try {
        await BrowserDB.createSketch({
          name: 'My Timeline',
          description: 'Personal forensic timeline',
          user_id: 'local-user',
          label_string: 'default',
          status: 'active',
        })
      } catch (e) {
        console.error('Error creating default sketch:', e)
      }
    },
    goToExplore() {
      this.loading = true
      // Navigate to explore view with default sketch (ID 1)
      this.$router.push({ name: 'Explore', params: { sketchId: 1 } })
    },
  },
}
</script>

<style scoped lang="scss">
.text-muted {
  color: rgba(0, 0, 0, 0.54);
}
</style>
