// added for WISPR-lab/data-export-gui
<template>
  <v-container class="pa-6 white min-h-100" style="max-width: 1100px;">

    <h1 class="text-h4 text--primary mb-6">Devices</h1>
    
    <p class="text-body-2 text--primary" style="line-height: 1.7;">
      Data exports often contain information about currently logged-in devices in addition to lists of login events associated with some information about the origin device. 
      LEStrADE attempts to unify this data using a two-level abstraction:
    </p>

    <ul class="text-body-2 text--primary mb-10" style="line-height: 1.7;">
      <li class="mb-2">
        <strong>Device Instance</strong>: A group of one or more raw records mapping to a trusted/registered device (e.g., for 2FA) or a group of login events linked by a common identifier (e.g., session ID or serial number) or tracked across browser/app upgrades.
      </li>
      <li>
        <strong>Device Profile</strong>: A super-group of one or more <strong>device instances</strong> that share the same hardware model (e.g., Apple iPhone 11). Since you may own more than one physical device of the same model, you can reassign <strong>instances</strong> to a new or different <strong>profile</strong> 
        by selecting "Edit" in the "Device Instances" list.
      </li>
    </ul>

    <!-- <v-row class="mb-6">
      <v-col cols="12" md="6">
        <div class="text-subtitle-1 text--primary mb-1">Device Instance</div>
        <p class="text-body-2 text--primary mb-0" style="line-height: 1.5;">
          A group of one or more raw records mapping to a trusted/registered device (e.g., for 2FA) or a group of login events linked by a common identifier (e.g., session ID or serial number) or tracked across browser/app upgrades.
        </p>
      </v-col>
      <v-col cols="12" md="6">
        <div class="text-subtitle-1 text--primary mb-1">Device Profile</div>
        <p class="text-body-2 text--primary mb-0" style="line-height: 1.5;">
          A super-group of one or more <strong>device instances</strong> that share the same hardware model (e.g., Apple iPhone 11).
          Since you may own more than one physical device of the same model, you can reassign <strong>instances</strong> to a new or different <strong>profile</strong>. 
        </p>
      </v-col>
    </v-row> -->

    <h3 class="text-h6 text--primary mb-2">Device Profiles ({{ devices.length }})</h3>

    <v-expansion-panels flat class="device-panels devices-list">
      <v-expansion-panel
        v-for="(dev, i) in devices"
        :key="i"
        class="mb-3 border rounded-xl overflow-hidden device-profile-card"
      >
        <v-expansion-panel-header class="pa-4" @click="onDeviceExpand">
          <template v-slot:default="{ open }">
            <device-profile-header :device="dev" :open="open" :ua-masking-text="uaMaskingText" @showJSON="showDeviceJSON" />
          </template>
        </v-expansion-panel-header>

        <v-expansion-panel-content class="grey lighten-5 border-top">
          <device-profile-dropdown
            :device="dev"
            :ua-masking-text="uaMaskingText"
            @change="saveDeviceChanges(dev)"
            @see-all-events="goToExplore(dev)"
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
      :source-profile-id="sourceProfileId"
      :is-loading="mergeLoading"
      :error="mergeError"
      @confirm="confirmGroup"
      @closed="onModalClosed"
    />

    <!-- Device JSON Modal -->
    <json-modal
      v-model="showJSONModal"
      :title="selectedDeviceForJSON ? ('Raw Data: ' + (selectedDeviceForJSON.user_label || selectedDeviceForJSON.model || selectedDeviceForJSON.label || 'Record')) : 'Data'"
      :data="selectedDeviceForJSON || {}"
      max-width="800"
    />

    <!-- Edit History Table Component -->
    <h3 class="text-h6 text--primary mb-2 font-weight-medium mt-12">Profile Edit History</h3>
    <p class="text-body-2 text--secondary mb-4">
      Edits you've made to device instances and profiles.
    </p>
    <user-device-edits-table :history-logs="historyLogs" :devices="devices" />
  </v-container>
</template>

<script>
import DeviceProfileDropdown from '@/components/Devices/DeviceProfileDropdown.vue';
import DeviceProfileHeader from '@/components/Devices/DeviceProfileHeader.vue';
import DeviceGroupModal from '@/components/Devices/DeviceGroupModal.vue';
import JSONModal from '@/components/Devices/JSONModal.vue';
import UserDeviceEditsTable from '@/components/Devices/UserDeviceEditsTable.vue';
import { getDevices, updateProfile, getInstanceRawAttrs } from '@/database/queries/devices_v2.js';
import { getUserDeviceEdits, moveInstancesToProfile, createProfileWithInstances } from '@/database/queries/user_device_edits.js';
import { titleCase } from '@/filters/TitleCase.js';

export default {
  name: 'Devices',
  components: {
    DeviceProfileDropdown,
    DeviceProfileHeader,
    DeviceGroupModal,
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
      showJSONModal: false,
      selectedDeviceForJSON: null,
      showDemoCompletionModal: false,
      uaMaskingText: {
        "mac_ipad": "To prevent fingerprinting, browsers on Apple iPads & Macs use generic User-Agents that hide the exact model and iOS version. Some iPads are misclassified as Macs.",
        "iphone": "To prevent fingerprinting, browsers on iPhones use generic User-Agents that hide the exact model.",
        "profile": "Multiple physical devices may be grouped under this generic profile."
      }
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
          result = await moveInstancesToProfile(
            this.selectedInstanceIdsToMove,
            payload.targetProfileId,
            payload.reason
          );
        } else {
          console.log('[confirmGroup] Creating profile:', payload.newProfileLabel, this.selectedInstanceIdsToMove);
          result = await createProfileWithInstances(
            this.selectedInstanceIdsToMove,
            payload.newProfileLabel,
            payload.reason
          );
        }

        console.log('[confirmGroup] Database write returned:', result);

        if (result && result.status === 'ok') {
          this.groupDialog = false;
          await this.fetchDevices();
          await this.fetchHistory();
        } else if (result) {
          this.mergeError = result.message || 'Action failed';
        } else {
          this.mergeError = 'Action failed: no response from database';
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
