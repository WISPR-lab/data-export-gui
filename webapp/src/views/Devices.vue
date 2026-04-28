<template>
  <v-container class="pa-6 white min-h-100" style="max-width: 900px;">
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


    <v-expansion-panels flat class="device-panels">
      <v-expansion-panel
        v-for="(dev, i) in devices"
        :key="i"
        class="mb-3 border rounded-xl overflow-hidden device-drop-zone"
        :class="{'drop-active': isDragging && activeDropId === i}"
        @dragover.native.prevent="activeDropId = i"
        @dragleave.native="activeDropId = null"
        @drop.native="onDrop($event, dev, i)"
      >
        <v-expansion-panel-header class="pa-4">
          <template v-slot:default="{ open }">
            <device-header :device="dev" :open="open" @showJSON="showDeviceJSON" />
          </template>
        </v-expansion-panel-header>

        <v-expansion-panel-content class="grey lighten-5 border-top">
          <device-detail-dropdown :device="dev" @change="saveDeviceChanges(dev)" @see-all-events="goToExplore(dev)" @unmerge="handleUnmerge(dev, $event)" @showJSON="showDeviceJSON" />
        </v-expansion-panel-content>
      </v-expansion-panel>
    </v-expansion-panels>


    <div v-if="unassigned.length > 0" class="mt-12 mb-10">
      <div class="mb-6">
        <h2 class="text-h6 font-weight-bold grey--text text--darken-4 mb-2">Sessions to Review</h2>
        <div class="body-1 grey--text text--darken-2">
            <p class="mb-1">These sessions are missing some specific device details. This usually happens when you use a web browser or private mode.</p>
            <p>They might belong to one of your devices above, or several of these records might actually be the same device.
            <!-- We couldn't automatically match these to specific device. This often happens when using private browsing mode or a different browser on your existing devices.  -->
            If you recognize them, <span class="font-weight-bold">drag and drop</span> them onto the correct profile above.</p>
        </div>
      </div>

      <v-expansion-panels flat class="device-panels">
        <v-expansion-panel
          v-for="(item, i) in unassigned"
          :key="i"
          class="mb-3 border rounded-xl overflow-hidden blue-grey lighten-5"
          draggable
          @dragstart.native="onDragStart($event, item)"
          @dragend.native="onDragEnd"
        >
          <v-expansion-panel-header class="pa-4">
            <template v-slot:default="{ open }">
              <device-header :device="item" is-generic :open="open" @showJSON="showDeviceJSON" />
            </template>
          </v-expansion-panel-header>

          <v-expansion-panel-content class="grey lighten-5 border-top">
            <device-detail-dropdown :device="item" is-generic @change="saveDeviceChanges(item)" @see-all-events="goToExplore(item)" @unmerge="handleUnmerge(item, $event)" @showJSON="showDeviceJSON" />
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </div>


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
import DeviceDetailDropdown from '@/components/Devices/DeviceDetailDropdown.vue';
import DeviceHeader from '@/components/Devices/DeviceHeader.vue';
import DeviceGroupModal from '@/components/Devices/DeviceGroupModal.vue';
import DeviceDetectionHelpModal from '@/components/Devices/DeviceDetectionHelpModal.vue';
import JSONModal from '@/components/Devices/JSONModal.vue';
import { getDevices, updateDeviceGroup } from '@/database/queries/devices.js';
import { callPyodideWorker } from '@/pyodide/pyodide-client';

export default {
  name: 'Devices',
  components: {
    DeviceDetailDropdown,
    DeviceHeader,
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
      unassigned: [],
      showDeviceHelpDialog: false,
      showJSONModal: false,
      selectedDeviceForJSON: null,
    }
  },
  async mounted() {
    await this.fetchDevices();
  },
  methods: {
    async fetchDevices() {
      try {
        const allGroups = await getDevices();
        this.devices = allGroups.filter(g => !g.is_generic);
        this.unassigned = allGroups.filter(g => g.is_generic);
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
        await updateDeviceGroup(device.id, {
          user_label: device.user_label,
          notes: device.notes
        });
        // Optionally re-fetch if needed, but the local state is already correct
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
    showDeviceJSON(data) {
      this.selectedDeviceForJSON = data.attributes || data
      this.showJSONModal = true
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
          const idx = this.unassigned.indexOf(this.staging.source);
          if (idx > -1) this.unassigned.splice(idx, 1);
          
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
    goToExplore(device) {
      const queryString = `device_profiles_data:${device.id}`;
      this.$router.push({
        name: 'Explore',
        query: { q: queryString }
      });
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
