<template>
  <v-dialog :value="dialogOpen" @input="setDialogOpen($event)" max-width="500px" persistent :z-index="25000">
    <v-card>
      <v-card-title class="headline">
        (Possible) Browser Incompatibility
        <v-spacer></v-spacer>
        <v-btn icon small @click="close"><v-icon>mdi-close</v-icon></v-btn>
      </v-card-title>

      <v-card-text>
        <p class="mb-3">
          Right now, this browser window hasn't been properly initialized to store your data safely.
        </p>
        <p class="mb-3">
          This might be just a temporary issue that can be fixed by <strong>reloading the page</strong>, or because your browser does not support the required features (common in private browsing or Safari).
        </p>
        <p class="mb-3">
          Please try clicking <strong>Clear app data &amp; reload</strong> below. If the issue persists, try opening the app in a <strong>different browser</strong> or a non-private window.
          If you click X, you can still browse documentation, but data import and event analysis are disabled.
        </p>

        <div v-if="opfsDiag" class="mb-4">
          <strong>Reason:</strong> {{ opfsDiag.cause }}
        </div>

        <v-expansion-panels flat tile class="mb-3">
          <v-expansion-panel>
            <v-expansion-panel-header class="px-0 font-weight-medium" style="min-height: 36px">
              Technical details
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-simple-table dense>
                <tbody>
                  <tr>
                    <td class="pl-0">crossOriginIsolated</td>
                    <td>false</td>
                  </tr>
                  <tr v-if="opfsDiag">
                    <td class="pl-0">SharedArrayBuffer</td>
                    <td>{{ opfsDiag.sabAvailable ? 'available' : 'unavailable' }}</td>
                  </tr>
                  <tr v-if="opfsDiag">
                    <td class="pl-0">Service worker supported</td>
                    <td>{{ opfsDiag.swSupported ? 'yes' : 'no' }}</td>
                  </tr>
                  <tr v-if="opfsDiag">
                    <td class="pl-0">coi-serviceworker registered</td>
                    <td>{{ opfsDiag.swRegistered ? 'yes' : 'no' }}</td>
                  </tr>
                  <tr v-if="opfsDiag">
                    <td class="pl-0">Intercepting this page load</td>
                    <td>{{ opfsDiag.swControlling ? 'yes' : 'no' }}</td>
                  </tr>
                </tbody>
              </v-simple-table>

              <div class="mt-3 font-weight-bold">More documentation:</div>
              <ul class="mt-1 pl-4">
                <li>
                  <a href="https://sqlite.org/wasm/doc/trunk/persistence.md#coop-coep" target="_blank" rel="noopener">
                    SQLite WASM &amp; OPFS persistence
                  </a>
                </li>
                <li>
                  <a href="https://github.com/gzuidhof/coi-serviceworker" target="_blank" rel="noopener">
                    coi-serviceworker library
                  </a>
                </li>
                <li>
                  <a href="https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API" target="_blank" rel="noopener">
                    MDN Service Worker API
                  </a>
                </li>
              </ul>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="error" text @click="wipe">Clear app data &amp; reload</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { diagnoseOpfsFailure } from '@/utils/opfsDiagnostics.js'
import { resetAllLocalData } from '@/database/index.js'
import EventBus from '@/event-bus.js'

export default {
  name: 'OpfsCompatibilityDialog',
  props: {
    value: {
      type: Boolean,
      default: false
    }
  },
  data: function() {
    return {
      internalOpen: false,
      opfsDiag: null
    }
  },
  computed: {
    dialogOpen: function() {
      return this.value || this.internalOpen
    }
  },
  watch: {
    dialogOpen: function(val) {
      if (val && !this.opfsDiag) {
        this.runDiagnostics()
      }
    }
  },
  mounted: function() {
    var self = this
    this._handler = function() {
      self.internalOpen = true
      self.runDiagnostics()
      self.navigateToCleanHome()
    }
    EventBus.$on('opfsUnavailable', this._handler)

    if (this.dialogOpen) {
      this.runDiagnostics()
      this.navigateToCleanHome()
    }
  },
  beforeDestroy: function() {
    if (this._handler) {
      EventBus.$off('opfsUnavailable', this._handler)
    }
  },
  methods: {
    navigateToCleanHome: function() {
      if (this.$route && (this.$route.path !== '/' || (this.$route.query && Object.keys(this.$route.query).length > 0))) {
        this.$router.replace({ path: '/' }).catch(function() {})
      }
    },
    setDialogOpen: function(val) {
      this.internalOpen = val
      this.$emit('input', val)
    },
    runDiagnostics: function() {
      var self = this
      diagnoseOpfsFailure().then(function(diag) {
        self.opfsDiag = diag
      })
    },
    close: function() {
      this.setDialogOpen(false)
      this.navigateToCleanHome()
    },
    wipe: function() {
      var self = this
      resetAllLocalData({ unregisterServiceWorkers: true }).then(function() {
        window.location.href = window.location.origin + window.location.pathname + '#/'
        window.location.reload();
      })
    }
  }
}
</script>
