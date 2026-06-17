// added for WISPR-lab/data-export-gui
<template>
  <v-container class="pa-6 white min-h-100" style="max-width: 1100px;">

    <h1 class="text-h4 font-weight-bold mb-6 text--primary">Devices</h1>
    
    <p class="text-body-1 text--primary mb-6" style="line-height: 1.7;">
      LEStrADE organizes your the raw data in your export about authenticated devices into a two-tier abstraction:
    </p>

    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-card flat color="grey lighten-5" height="100%" class="pa-4 text-body-2 text--primary">
          <strong>Device Instance</strong>:  
          A group of one or more raw records mapping to a trusted/registered device (e.g., for 2FA) or a group of login events linked by a common identifier (e.g., session ID or serial number) or tracked across browser/app upgrades.
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card flat color="grey lighten-5" height="100%" class="pa-4 text-body-2 text--primary">
          <strong>Device Profile</strong>: 
          A super-group of one or more <strong>device instances</strong> that share the same hardware model (e.g., Apple iPhone 11).
          Since you may own more than one physical device of the same model, you can reassign <strong>instances</strong> to a new or different <strong>profile</strong>. 
        </v-card>
      </v-col>
    </v-row>

    <h3 class="text-h6 font-weight-bold mb-2 text--primary">Device Profiles ({{ devices.length }})</h3>

    <v-expansion-panels flat class="device-panels devices-list">
      <v-expansion-panel
        v-for="(dev, i) in devices"
        :key="i"
        class="mb-3 border rounded-xl overflow-hidden device-profile-card"
      >
        <v-expansion-panel-header class="pa-4" @click="onDeviceExpand">
          <template v-slot:default="{ open }">
            <device-profile-header :device="dev" :open="open" @showJSON="showDeviceJSON" />
          </template>
        </v-expansion-panel-header>

        <v-expansion-panel-content class="grey lighten-5 border-top">
          <device-profile-dropdown
            :device="dev"
            @change="saveDeviceChanges(dev)"
            @see-all-events="goToExplore(dev)"
            @unmerge="handleUnmerge(dev, $event)"
            @batch-unmerge="handleBatchUnmerge(dev, $event)"
            @move-instances="openMoveDialog(dev, $event)"
            @create-profile="openCreateDialog(dev, $event)"
            @showJSON="showDeviceJSON"
          />
        </v-expansion-panel-content>
      </v-expansion-panel>
    </v-expansion-panels>

    <device-group-modal 
      v-model="groupDialog" 
      :mode="editMode"
      :selected-instance-ids-to-move="selectedInstanceIdsToMove"
      :existing-profiles="devices"
      :current-profile-id="sourceProfileId"
      :is-loading="mergeLoading"
      :error="mergeError"
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

    <!-- Edit History Table Component -->
    <user-device-edits-table :history-logs="historyLogs" :devices="devices" />
  </v-container>
</template>

<script>
import DeviceProfileDropdown from '@/components/Devices/DeviceProfileDropdown.vue';
import DeviceProfileHeader from '@/components/Devices/DeviceProfileHeader.vue';
import DeviceGroupModal from '@/components/Devices/DeviceGroupModal.vue';
import DeviceDetectionHelpModal from '@/components/Devices/DeviceDetectionHelpModal.vue';
import JSONModal from '@/components/Devices/JSONModal.vue';
import UserDeviceEditsTable from '@/components/Devices/UserDeviceEditsTable.vue';
import { getDevices, updateProfile, getInstanceRawAttrs, getUserDeviceEdits, createUserDeviceEdit } from '@/database/queries/devices_v2.js';
import { callPyodideWorker } from '@/pyodide/pyodide-client';

export default {
  name: 'Devices',
  components: {
    DeviceProfileDropdown,
    DeviceProfileHeader,
    DeviceGroupModal,
    DeviceDetectionHelpModal,
    'json-modal': JSONModal,
    UserDeviceEditsTable
  },
  data() {
    return {
      groupDialog: false,
      editMode: 'move', // 'move' or 'create'
      selectedInstanceIdsToMove: [],
      sourceProfileId: '',
      mergeLoading: false,
      mergeError: null,
      devices: [],
      historyLogs: [],
      showDeviceHelpDialog: false,
      showJSONModal: false,
      selectedDeviceForJSON: null,
      showDemoCompletionModal: false,
    }
  },
  watch: {
    '$store.state.demoInProgress'(newVal, oldVal) {
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
    await this.fetchHistory();
    
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
    async fetchHistory() {
      try {
        this.historyLogs = await getUserDeviceEdits();
      } catch (err) {
        console.error('Failed to fetch history logs:', err);
      }
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
          // Log unlink action
          const summaryText = 'Session [ID: ' + atomicId.substring(0, 4) + '...]';
          await createUserDeviceEdit({
            action_type: 'move_instances',
            instance_ids: [atomicId],
            instance_summaries: [summaryText],
            source_profile_id: device.id,
            source_profile_label: this.getProfileLabelById(device.id),
            target_profile_id: result.new_profile_id || null,
            target_profile_label: 'New Standalone Profile',
            reason: 'Unlinked session from profile'
          });
          
          await this.fetchDevices();
          await this.fetchHistory();
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
            // Log unlink action
            const summaryText = 'Session [ID: ' + atomicId.substring(0, 4) + '...]';
            await createUserDeviceEdit({
              action_type: 'move_instances',
              instance_ids: [atomicId],
              instance_summaries: [summaryText],
              source_profile_id: device.id,
              source_profile_label: this.getProfileLabelById(device.id),
              target_profile_id: result.new_profile_id || null,
              target_profile_label: 'New Standalone Profile',
              reason: 'Unlinked session from profile (Batch action)'
            });
            successCount++;
          } else {
            console.error('Batch unmerge failed for atomicId:', atomicId, result);
          }
        }
        if (successCount > 0) {
          await this.fetchDevices();
          await this.fetchHistory();
        }
      } catch (error) {
        console.error('Batch unmerge error:', error);
      }
    },
    openMoveDialog(device, instanceIds) {
      this.editMode = 'move';
      this.selectedInstanceIdsToMove = instanceIds;
      this.sourceProfileId = device.id;
      this.mergeError = null;
      this.groupDialog = true;
    },
    openCreateDialog(device, instanceIds) {
      this.editMode = 'create';
      this.selectedInstanceIdsToMove = instanceIds;
      this.sourceProfileId = device.id;
      this.mergeError = null;
      this.groupDialog = true;
    },
    async confirmGroup(payload) {
      try {
        this.mergeLoading = true;
        this.mergeError = null;

        let result;
        if (payload.mode === 'move') {
          console.log('[confirmGroup] Moving instances:', payload.targetProfileId, this.selectedInstanceIdsToMove);
          result = await callPyodideWorker('move_instances', {
            instanceIds: this.selectedInstanceIdsToMove,
            targetProfileId: payload.targetProfileId,
            reason: payload.reason
          });
        } else {
          console.log('[confirmGroup] Creating profile:', payload.newProfileLabel, this.selectedInstanceIdsToMove);
          result = await callPyodideWorker('create_profile', {
            instanceIds: this.selectedInstanceIdsToMove,
            newProfileLabel: payload.newProfileLabel,
            reason: payload.reason
          });
        }

        console.log('[confirmGroup] Worker returned:', result);

        if (result && result.status === 'ok') {
          // Log User Edits
          const instanceSummaries = this.getInstanceSummaries(this.selectedInstanceIdsToMove);
          const sourceProfileLabel = this.getProfileLabelById(this.sourceProfileId);
          
          if (payload.mode === 'create') {
            const newProfileId = result.new_profile_id || 'new-profile';
            
            // Log 1: Profile Creation
            await createUserDeviceEdit({
              action_type: 'create_profile',
              instance_ids: [],
              instance_summaries: [],
              source_profile_id: null,
              target_profile_id: newProfileId,
              source_profile_label: null,
              target_profile_label: payload.newProfileLabel,
              reason: 'User created profile'
            });

            // Log 2: Move Instances
            await createUserDeviceEdit({
              action_type: 'move_instances',
              instance_ids: this.selectedInstanceIdsToMove,
              instance_summaries: instanceSummaries,
              source_profile_id: this.sourceProfileId,
              target_profile_id: newProfileId,
              source_profile_label: sourceProfileLabel,
              target_profile_label: payload.newProfileLabel,
              reason: payload.reason
            });
          } else {
            // Log Move
            const targetProfileLabel = this.getProfileLabelById(payload.targetProfileId);
            await createUserDeviceEdit({
              action_type: 'move_instances',
              instance_ids: this.selectedInstanceIdsToMove,
              instance_summaries: instanceSummaries,
              source_profile_id: this.sourceProfileId,
              target_profile_id: payload.targetProfileId,
              source_profile_label: sourceProfileLabel,
              target_profile_label: targetProfileLabel,
              reason: payload.reason
            });
          }

          this.groupDialog = false;
          await this.fetchDevices();
          await this.fetchHistory();
        } else if (result) {
          this.mergeError = result.message || 'Action failed';
        } else {
          this.mergeError = 'Action failed: no response from worker';
        }
      } catch (error) {
        this.mergeError = (error && error.message) || 'Action failed';
        console.log('[confirmGroup] Error:', error);
      } finally {
        this.mergeLoading = false;
      }
    },
    onModalClosed() {
      this.selectedInstanceIdsToMove = [];
      this.sourceProfileId = '';
    },
    getInstanceSummaries(instanceIds) {
      const summaries = [];
      const self = this;
      instanceIds.forEach(function(id) {
        let found = null;
        self.devices.forEach(function(d) {
          if (d.instances) {
            const inst = d.instances.find(function(i) { return i.id === id; });
            if (inst) found = inst;
          }
        });
        if (found) {
          const appName = (found.ua_summary && found.ua_summary.primary) || found.client_name || 'Session';
          const os = found.os_name || found.os_type || 'Unknown OS';
          const dates = found.first_seen ? new Date(found.first_seen * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '';
          let text = appName + ' on ' + os;
          if (dates) text += ' (Active: ' + dates + ')';
          text += ' [ID: ' + id.substring(0, 4) + '...]';
          summaries.push(text);
        } else {
          summaries.push('Session [ID: ' + id.substring(0, 4) + '...]');
        }
      });
      return summaries;
    },
    getProfileLabelById(profileId) {
      if (!profileId) return '';
      const p = this.devices.find(function(d) { return d.id === profileId; });
      if (p) {
        return p.user_label || p.model || 'Unknown Profile';
      }
      return '';
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
.border-top { border-top: 1px solid rgba(0,0,0,0.12) !important; }

.rounded-xl { border-radius: 12px !important; }

.device-panels ::v-deep .v-expansion-panel-header--active {
  background-color: #f8f9fa;
}

.v-expansion-panel::before {
  box-shadow: none !important;
}
</style>
