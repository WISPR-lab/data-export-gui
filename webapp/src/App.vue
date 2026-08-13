<!--
Copyright 2019 Google Inc. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

<!-- NOTICE --- MODIFIED FOR WISPR-lab/data-export-gui -->
<template>
  <v-app id="app">
    <!-- Global snackbar -->
    <v-snackbar v-model="snackbar.active" :timeout="snackbar.timeout" :color="snackbar.color" top>
      {{ snackbar.message }}
      <template v-slot:action="{ attrs }">
        <v-btn text v-bind="attrs" @click="snackbar.active = false"> Close </v-btn>
      </template>
    </v-snackbar>

    <!-- OPFS / cross-origin isolation incompatibility warning -->
    <opfs-compatibility-dialog v-model="opfsDialog" />
    <!-- shown when a SQL query fails with "no such table/column") -->
    <schema-refresh-dialog v-model="schemaDialog" />

    <!-- Main router view -->
    <router-view></router-view>

    <!-- Compare View Overlay -->
    <compare-events-dialog />

    <!-- Interactive Demo Overlay -->
    <demo-overlay />
  </v-app>
</template>

<script>
import EventBus from './event-bus.js'
import { initShutdownDetection, initInactivityDetection } from '@/utils/shutdownDetection.js'
import DemoOverlay from '@/components/Demo/DemoOverlay.vue'
import CompareEventsDialog from '@/components/Events/CompareEventsDialog.vue'
import OpfsCompatibilityDialog from '@/components/OpfsCompatibilityDialog.vue'
import SchemaRefreshDialog from '@/components/SchemaRefreshDialog.vue'

export default {
  name: 'app',
  components: {
    DemoOverlay,
    CompareEventsDialog,
    OpfsCompatibilityDialog,
    SchemaRefreshDialog,
  },
  data: function() {
    return {
      opfsDialog: false,
      schemaDialog: false,
    }
  },
  computed: {
    snackbar() {
      return this.$store.state.snackbar
    },
  },
  watch: {
    $route: function() {
      if (this.checkOpfsIncompatibility()) {
        this.opfsDialog = true
      }
    }
  },
  methods: {
    checkOpfsIncompatibility: function() {
      if (window.crossOriginIsolated) return false

      const sabMissing = typeof SharedArrayBuffer === 'undefined'
      const reloadAttempted = !!sessionStorage.getItem('coi_reload_attempted')
      const currentRoute = this.$route
      const routeRequiresOpfs = currentRoute && currentRoute.meta && currentRoute.meta.requiresOpfs

      return sabMissing || reloadAttempted || routeRequiresOpfs
    },
    setErrorSnackBar: function (message) {
      const snackbar = {
        message: message,
        color: 'error',
        timeout: 7000,
      }
      this.$store.dispatch('setSnackBar', snackbar)
    },
    _initShutdownDetection() {
      initShutdownDetection(this.$store)
    },
    _initInactivityDetection() {
      // Demo mode has no real local data to protect - skip.
      if (this.$store.state.demoMode) return
      initInactivityDetection(this.$store)
    },
  },
  mounted() {
    // Listen on errors from REST API calls
    EventBus.$on('errorSnackBar', this.setErrorSnackBar)
    // Show modal if DB layer or router guard emits opfsUnavailable
    EventBus.$on('opfsUnavailable', function() { this.opfsDialog = true; }.bind(this))
    EventBus.$on('schemaMismatch', function() { this.schemaDialog = true; }.bind(this))

    if (window.opfsUnavailable || this.checkOpfsIncompatibility()) {
      this.opfsDialog = true;
    }

    const isDark = localStorage.getItem('isDarkTheme')
    if (isDark) {
      if (isDark === 'true') {
        this.$vuetify.theme.dark = true
      } else {
        this.$vuetify.theme.dark = false
      }
    }
    let element = document.body
    element.dataset.theme = this.$vuetify.theme.dark ? 'dark' : 'light'

    this._initShutdownDetection()
    this._initInactivityDetection()
  },
  beforeDestroy() {
    EventBus.$off('errorSnackBar')
    EventBus.$off('opfsUnavailable')
    EventBus.$off('schemaMismatch')
  },
}
</script>

<style lang="scss"></style>
