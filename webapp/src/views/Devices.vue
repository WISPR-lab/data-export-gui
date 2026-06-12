// added for WISPR-lab/data-export-gui
<template>
  <v-container class="pa-6 white min-h-100" style="max-width: 900px;">
    <!-- Demo completion modal -->
    <v-dialog v-model="showDemoCompletionModal" width="500" persistent>
      <v-card class="pa-6">
        <v-card-title class="text-h5 mb-4">Excellent! 🎉</v-card-title>
        <v-card-text>
          <p>You've seen the main features of the data explorer. Now you're ready to analyze your own data.</p>
          <p class="mt-4 mb-0">Would you like to upload your data now, or explore the demo a bit more?</p>
        </v-card-text>
        <v-card-actions class="pt-4">
          <v-spacer></v-spacer>
          <v-btn text @click="exploreMoreDemo">Explore More</v-btn>
          <v-btn text @click="returnToHome">Return Home</v-btn>
          <v-btn color="primary" @click="goToUpload">Upload Your Data</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <div class="mb-8">
      <h1 class="text-h4 font-weight-bold mb-2">Your devices</h1>
      <p class="body-1 grey--text text--darken-2">
        We found activity from these devices in your data export(s). You can label devices as malicious or give them custom names to keep track of them.
        <v-btn
          text
          small
          color="primary"
          @click="showDeviceHelpDialog = true"
          class="pa-0 ml-1"
        >
          Learn more
          <v-icon small class="ml-1">mdi-help-circle-outline</v-icon>
        </v-btn>
      </p>
    </div>


    <v-expansion-panels flat class="device-panels devices-list">
      <v-expansion-panel
        v-for="(dev, i) in devices"
        :key="i"
        class="mb-3 border rounded-xl overflow-hidden device-drop-zone device-profile-card"
        :class="{'drop-active': isDragging && activeDropId === i}"
        :draggable="false"
        @dragstart.native="onDragStart($event, dev)"
        @dragend.native="onDragEnd"
        @dragover.native.prevent="activeDropId = i"
        @dragleave.native="activeDropId = null"
        @drop.native="onDrop($event, dev, i)"
      >
        <v-expansion-panel-header class="pa-4" @click="onDeviceExpand">
          <template v-slot:default="{ open }">
            <device-profile-header :device="dev" :open="open" @showJSON="showDeviceJSON" />
          </template>
        </v-expansion-panel-header>

        <v-expansion-panel-content class="grey lighten-5 border-top">
          <device-profile-dropdown :device="dev" @change="saveDeviceChanges(dev)" @see-all-events="goToExplore(dev)" @unmerge="handleUnmerge(dev, $event)" @batch-unmerge="handleBatchUnmerge(dev, $event)" @showJSON="showDeviceJSON" />
        </v-expansion-panel-content>
      </v-expansion-panel>
    </v-expansion-panels>


    <device-group-modal 
      v-model="groupDialog" 
      :source="staging ? staging.source : null" 
      :target="staging ? staging.target : null"
      :is-loading="mergeLoading"
      :error="mergeError"
      :success="mergeSuccess"
      @confirm="confirmGroup"
      @closed="onModalClosed"
    />

    <device-detection-help-modal v-model="showDeviceHelpDialog" />

    <!-- Device JSON Modal -->
    <json-modal
      v-model="showJSONModal"
      :title="selectedDeviceForJSON ? ('Raw Data: ' + (selectedDeviceForJSON.user_label || selectedDeviceForJSON.model || selectedDeviceForJSON.label || 'Record')) : 'Data'"
      :data="selectedDeviceForJSON || {}"
      max-width="800"
    />
  </v-container>
</template>

<script>
import DeviceProfileDropdown from '@/components/Devices/DeviceProfileDropdown.vue';
import DeviceProfileHeader from '@/components/Devices/DeviceProfileHeader.vue';
import DeviceGroupModal from '@/components/Devices/DeviceGroupModal.vue';
import DeviceDetectionHelpModal from '@/components/Devices/DeviceDetectionHelpModal.vue';
import JSONModal from '@/components/Devices/JSONModal.vue';
import { getDevices, updateProfile, getInstanceRawAttrs } from '@/database/queries/devices_v2.js';
import { callPyodideWorker } from '@/pyodide/pyodide-client';

export default {
  name: 'Devices',
  components: {
    DeviceProfileDropdown,
    DeviceProfileHeader,
    DeviceGroupModal,
    DeviceDetectionHelpModal,
    'json-modal': JSONModal
  },
  data() {
    return {
      isDragging: false,
      activeDropId: null,
      groupDialog: false,
      mergeLoading: false,
      mergeError: null,
      mergeSuccess: false,
      selectedRecord: null,
      staging: null,
      devices: [],
      showDeviceHelpDialog: false,
      showJSONModal: false,
      selectedDeviceForJSON: null,
      showDemoCompletionModal: false,
    }
  },
  watch: {
    '$store.state.demoInProgress'(newVal, oldVal) {
      // Show completion modal when demo finishes (demoInProgress changes from true to false)
      if (oldVal && !newVal && this.$store.state.demoMode) {
        console.log('[Devices] Demo completed, showing completion modal');
        this.$nextTick(() => {
          this.showDemoCompletionModal = true
        })
      }
    }
  },
  async mounted() {
    await this.fetchDevices();
    
    // Auto-resume demo if in demo mode
    if (this.$store.state.demoMode && this.$store.state.demoInProgress) {
      console.log('[Devices] Resuming demo');
      this.$nextTick(() => {
        this.resumeDemo();
      });
    }
  },
  methods: {
    async fetchDevices() {
      try {
        this.devices = await getDevices();
      } catch (err) {
        console.error('Failed to fetch devices:', err);
      }
    },
    getSoftware(device) {
      if (!device.os_name && !device.os_version) return null;
      const parts = [];
      if (device.os_name) parts.push(String(device.os_name));
      if (device.os_version) parts.push(String(device.os_version));
      return parts.length ? parts.join(' ') : null;
    },
    async saveDeviceChanges(device) {
      try {
        await updateProfile(device.id, {
          user_label: device.user_label,
          notes: device.notes
        });
      } catch (err) {
        console.error('Failed to save device changes:', err);
      }
    },
    async handleUnmerge(device, atomicId) {
      try {
        const result = await callPyodideWorker('unmerge', {
          profileId: device.id,
          atomicId: atomicId
        });
        
        if (result && result.status === 'ok') {
          await this.fetchDevices();
        } else {
          console.error('Unmerge failed:', result);
        }
      } catch (error) {
        console.error('Unmerge error:', error);
      }
    },
    async handleBatchUnmerge(device, atomicIds) {
      try {
        let successCount = 0;
        for (const atomicId of atomicIds) {
          const result = await callPyodideWorker('unmerge', {
            profileId: device.id,
            atomicId: atomicId
          });
          if (result && result.status === 'ok') {
            successCount++;
          } else {
            console.error('Batch unmerge failed for atomicId:', atomicId, result);
          }
        }
        if (successCount > 0) {
          await this.fetchDevices();
        }
      } catch (error) {
        console.error('Batch unmerge error:', error);
      }
    },
    async showDeviceJSON(data) {
      if (data && data.id && !data.instances) {
        try {
          const rawAttrs = await getInstanceRawAttrs(data.id);
          this.selectedDeviceForJSON = rawAttrs;
        } catch (e) {
          console.error('Failed to load instance attributes:', e);
          this.selectedDeviceForJSON = data;
        }
      } else {
        this.selectedDeviceForJSON = data.attributes || data;
      }
      this.showJSONModal = true;
    },
    onDragStart(event, item) {
      this.isDragging = true;
      this.selectedRecord = item;
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', JSON.stringify(item));
    },
    onDragEnd() {
      this.isDragging = false;
      this.activeDropId = null;
    },
    onDrop(event, targetDevice, index) {
      if (!this.selectedRecord) return;
      this.staging = { source: this.selectedRecord, target: targetDevice, index };
      this.mergeError = null;  // Clear previous error when starting new merge
      this.groupDialog = true;
      this.activeDropId = null;
    },
    async confirmGroup() {
      try {
        this.mergeLoading = true;
        this.mergeError = null;

        console.log('[confirmGroup] Starting merge with:', { src: this.staging.source.id, tgt: this.staging.target.id });
        const result = await callPyodideWorker('merge', {
          srcProfileId: this.staging.source.id,
          tgtProfileId: this.staging.target.id
        });
        console.log('[confirmGroup] Worker returned:', result);

        if (result && result.status === 'ok') {
          this.mergeSuccess = true;

          if (this.$store.state.demoMode) {
            const EventBus = require('@/event-bus.js').default
            EventBus.$emit('demo:action', 'device-dropped')
          }

          await this.fetchDevices();
        } else if (result && result.status === 'ineligible') {
          this.mergeError = result.message;
        } else if (result) {
          this.mergeError = result.message || 'Merge failed';
        } else {
          this.mergeError = 'Merge failed: no response from worker';
        }
      } catch (error) {
        this.mergeError = (error && error.message) || 'Merge failed';
        console.log('[confirmGroup] Merge error:', error);
      } finally {
        this.mergeLoading = false;
      }
    },
    cancelGroup() {
      this.groupDialog = false;
      this.staging = null;
      this.selectedRecord = null;
      this.mergeLoading = false;
      this.mergeError = null;
    },
    onModalClosed() {
      this.mergeSuccess = false;
    },
    onDeviceExpand() {
      if (this.$store.state.demoMode) {
        const EventBus = require('@/event-bus.js').default
        EventBus.$emit('demo:action', 'device-expanded')
      }
    },
    goToExplore(device) {
      const queryString = `device_profiles_data:${device.id}`;
      const routeName = this.$route.name === 'DemoDevices' ? 'DemoExplore' : 'Explore'
      this.$router.push({
        name: routeName,
        query: { q: queryString }
      });
    },
    resumeDemo() {
      console.log('[Devices] Resuming demo');
      const DemoController = require('@/demo/DemoController.js').default
      // TODO Note: We don't have a specific resume yet in DemoController, but we could add one if needed.
    },
    goToUpload() {
      console.log('[Devices] User chose to upload data');
      this.showDemoCompletionModal = false
      this.$store.dispatch('clearDemoState')
      this.$store.commit('SET_DEMO_MODE', false)
      this.$router.push('/')
    },
    returnToHome() {
      console.log('[Devices] User chose to return home');
      this.showDemoCompletionModal = false
      this.$store.dispatch('clearDemoState')
      this.$store.commit('SET_DEMO_MODE', false)
      this.$router.push('/')
    },
    exploreMoreDemo() {
      console.log('[Devices] User chose to explore more');
      this.showDemoCompletionModal = false
    }
  }
};
</script>

<style scoped>
.min-h-100 { min-height: 100vh; }
.white { background-color: #ffffff !important; }
.border { border: 1px solid rgba(0,0,0,0.12) !important; }
.border-dark { border: 1px solid rgba(0,0,0,0.24) !important; }
.border-top { border-top: 1px solid rgba(0,0,0,0.12) !important; }
.border-bottom { border-bottom: 1px solid rgba(0,0,0,0.12) !important; }
.border-blue-grey { border: 1px solid #cfd8dc !important; }
.gap-3 { gap: 12px; }

.rounded-xl { border-radius: 12px !important; }

.unassigned-chip {
  min-width: 180px;
  flex-shrink: 0;
  cursor: grab;
}

.device-panels ::v-deep .v-expansion-panel-header--active {
  background-color: #f8f9fa;
}

.device-drop-zone {
  transition: border 0.1s ease;
}

.drop-active {
  border: 1px solid #1976d2 !important;
  background-color: #e3f2fd !important;
}

/* Remove default shadow for a cleaner look */
.v-expansion-panel::before {
  box-shadow: none !important;
}
</style>
