// added for WISPR-lab/data-export-gui
<template>
  <div class="pa-6">
    <!-- 1. Device Details Table (at the very top, transparent background) -->
    <div v-if="profileAttributesTable.length > 0" class="mb-6">
      <div class="overline mb-3">Device Details</div>
      <device-attributes-table :attributes="profileAttributesTable" />
    </div>

    <!-- <v-divider v-if="profileAttributesTable.length > 0" class="mb-6"></v-divider> -->

    <!-- 2. Name & Notes Inputs -->
    <div class="d-flex mb-6" style="gap: 36px;">
      <div style="flex: 0 0 auto; width: 300px;">
        <div class="overline">Name</div>
        
        <div class="mb-8">
          <v-text-field
            v-model="device.user_label"
            placeholder="e.g. Work Phone"
            outlined
            dense
            class="rounded-lg"
            hide-details
            @change="$emit('change')"
          ></v-text-field>
        </div>
      </div>

      <!-- Right Column: Notes (tall, expands) -->
      <div style="flex: 1 0 auto;">
        <div class="overline">Notes</div>
        <v-textarea
          v-model="device.notes"
          placeholder="Add any personal notes about this device."
          outlined
          dense
          rows="1"
          class="rounded-lg"
          hide-details
          @change="$emit('change')"
        ></v-textarea>
      </div>
    </div>

    <v-divider class="mb-6"></v-divider>

    <!-- 3. Device Instances -->
    <div v-if="device.instances && device.instances.length > 0" class="mb-6">
      <div class="d-flex align-center justify-space-between mb-3">
        <div class="d-flex align-center">
          <span class="overline">Device Instances ({{ device.instances.length }})</span>
          <v-btn icon x-small class="ml-1" color="primary" @click="showHelpModal = true" title="What is a device instance?">
            <v-icon small>mdi-help-circle-outline</v-icon>
          </v-btn>
        </div>
        <v-btn
          v-if="device.instances.length > 1"
          text
          small
          color="grey darken-1"
          class="rounded-lg text-none px-2"
          @click="toggleEditMode"
        >
          {{ isEditingInstances ? 'Done' : 'Edit' }}
        </v-btn>
      </div>

      <!-- Batch Action Bar (Edit mode) -->
      <div v-if="isEditingInstances" class="d-flex align-center justify-space-between mb-4 pa-3 border rounded-lg bg-light-grey">
        <div class="d-flex align-center">
          <v-checkbox
            :input-value="isAllSelected"
            :indeterminate="isPartiallySelected"
            hide-details
            class="ma-0 pa-0 mr-3"
            @change="toggleSelectAll"
          ></v-checkbox>
          <span class="body-2 font-weight-medium">{{ selectedInstanceIds.length }} selected</span>
        </div>
        <v-btn
          color="error"
          small
          outlined
          :disabled="selectedInstanceIds.length === 0"
          class="rounded-lg"
          @click="batchUnlink"
        >
          <v-icon left small>mdi-link-off</v-icon>
          Unlink Selected
        </v-btn>
      </div>

      <div class="space-y-2" style="display: flex; flex-direction: column; gap: 12px;">
        <DeviceInstance
          v-for="inst in device.instances"
          :key="inst.id"
          :instance="inst"
          :show-checkbox="isEditingInstances"
          :selected="selectedInstanceIds.includes(inst.id)"
          :show-help="isFirstOfType(inst)"
          @select="toggleInstanceSelection(inst.id, $event)"
          @showJSON="$emit('showJSON', $event)"
          @unmerge="$emit('unmerge', $event)"
        />
      </div>
    </div>

    <!-- Device Instances Explanation Modal -->
    <v-dialog v-model="showHelpModal" max-width="500px">
      <v-card class="pa-4 rounded-xl">
        <v-card-title class="text-h6 font-weight-bold d-flex align-center">
          <v-icon color="primary" class="mr-2">mdi-information-outline</v-icon>
          Profiles vs. Instances
        </v-card-title>
        <v-card-text class="pt-2">
          <p class="body-2">
            This tool separates device data into a hierarchy to help map your timeline:
          </p>
          <div class="mb-4">
            <div class="subtitle-2 font-weight-bold primary--text">Device Profile</div>
            <div class="body-2 text--secondary">
              Formed by connecting instances that share the same hardware model  (e.g. all <i>iPhone XRs</i> or all <i>MacBooks</i>). TODO caveat about masking/deterministic IDs
            </div>
          </div>
          <div class="mb-4">
            <div class="subtitle-2 font-weight-bold primary--text">Device Instance</div>
            <div class="body-2 text--secondary">
              A single continuous installation or session chain (e.g. a specific <i>Instagram App</i> setup or <i>Safari browser session</i>) representing an individual device deployment.
            </div>
          </div>
          <p class="body-2 mb-0">

          </p>
        </v-card-text>
        <v-card-actions class="justify-end">
          <v-btn color="primary" text @click="showHelpModal = false">Got it</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import DeviceInstance from './DeviceInstance.vue';
import DeviceAttributesTable from './DeviceAttributesTable.vue';
import { getProfileRawAttrs, getCondensedModel, getCondensedOS } from '@/database/queries/devices_v2.js';
import { titleCase } from '@/filters/TitleCase.js';

export default {
  name: 'DeviceProfileDropdown',
  components: {
    DeviceInstance,
    DeviceAttributesTable
  },
  props: {
    device: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      rawAttributes: {},
      showHelpModal: false,
      isEditingInstances: false,
      selectedInstanceIds: []
    }
  },
  watch: {
    device: {
      immediate: true,
      handler: 'loadAttributes'
    }
  },
  computed: {
    isAllSelected() {
      if (!this.device.instances || this.device.instances.length === 0) return false;
      return this.selectedInstanceIds.length === this.device.instances.length;
    },
    isPartiallySelected() {
      return this.selectedInstanceIds.length > 0 && this.selectedInstanceIds.length < this.device.instances.length;
    },
    profileAttributesTable() {
      // Construct OS field
      const osName = this.device.latest_os_name || this.device.os_name || this.device.latest_os_type || this.device.os_type || '';
      const versions = (this.device.all_os_versions || []).filter(Boolean);
      const osValue = getCondensedOS(osName, versions);

      const uniqueIPs = [...new Set((this.device.instances || []).flatMap(inst => inst.client_ips || []))].filter(ip => {
        if (!ip) return false;
        const ipStr = String(ip).trim().toLowerCase();
        return ipStr !== '' && ipStr !== 'null' && ipStr !== 'none' && ipStr !== 'unknown' && ipStr !== 'undefined';
      });

      // Condense Manufacturer and Model into a single 'Model' value
      const modelValue = getCondensedModel(this.device.manufacturer, this.device.model);

      // Core attributes list (filtered to exclude empty / unknown values)
      const coreCandidates = [
        { label: 'Model', value: modelValue },
        { label: 'OS', value: osValue },
        { label: 'First Active', value: this.device.first_seen, isTimestamp: true },
        { label: 'Last Active', value: this.device.last_seen, isTimestamp: true },
        { label: 'IP Addresses', value: uniqueIPs }
      ];

      const core = coreCandidates.filter(item => {
        if (item.value === null || item.value === undefined) return false;
        if (Array.isArray(item.value)) return item.value.length > 0;
        if (item.isTimestamp) {
          const num = Number(item.value);
          if (isNaN(num) || num <= 0) return false;
        }
        const valStr = String(item.value).trim();
        const lower = valStr.toLowerCase();
        return valStr !== '' && lower !== 'unknown' && lower !== 'null' && lower !== 'none' && lower !== 'undefined';
      });

      // Optional hardware fields
      const optionalKeys = [
        { key: 'device.given_name', label: 'Device Name' },
        { key: 'device.name', label: 'Device Name' },
        { key: 'serial_number', label: 'Serial Number' },
        { key: 'serialnumber', label: 'Serial Number' },
        { key: 'mac_address', label: 'MAC Address' },
        { key: 'wifi_mac', label: 'MAC Address' },
        { key: 'wifiMac', label: 'MAC Address' },
        { key: 'imei', label: 'IMEI' },
        { key: 'device.imei', label: 'IMEI' },
        { key: 'meid', label: 'MEID' },
        { key: 'device.meid', label: 'MEID' },
        { key: 'device.id.android', label: 'Android ID' },
        { key: 'device.product.id', label: 'Hardware Product ID' },
        { key: 'device.id.google.ad', label: 'Google Advertiser ID' },
        { key: 'device.id.google', label: 'Google Device ID' },
        { key: 'device.id.facebook', label: 'Facebook Device ID' },
        { key: 'device.id.facebook.ad', label: 'Facebook Advertiser ID' },
        { key: 'udid', label: 'UDID' },
        { key: 'uuid', label: 'UUID' }
      ];

      const optionals = [];
      optionalKeys.forEach(opt => {
        const actualKey = Object.keys(this.rawAttributes).find(k => k.toLowerCase() === opt.key.toLowerCase());
        if (actualKey) {
          const val = this.rawAttributes[actualKey];
          if (val !== null && val !== undefined) {
            const valStr = String(val).trim();
            const lower = valStr.toLowerCase();
            if (valStr !== '' && lower !== 'unknown' && lower !== 'null' && lower !== 'none' && lower !== 'undefined') {
              if (!optionals.some(x => x.label === opt.label)) {
                optionals.push({ label: opt.label, value: valStr });
              }
            }
          }
        }
      });

      return [...core, ...optionals];
    }
  },
  methods: {
    async loadAttributes() {
      if (this.device && this.device.id) {
        try {
          this.rawAttributes = await getProfileRawAttrs(this.device.id);
        } catch (e) {
          console.error('Failed to load profile attributes:', e);
        }
      }
    },
    toggleEditMode() {
      this.isEditingInstances = !this.isEditingInstances;
      if (!this.isEditingInstances) {
        this.selectedInstanceIds = [];
      }
    },
    toggleInstanceSelection(instanceId, isSelected) {
      if (isSelected) {
        if (!this.selectedInstanceIds.includes(instanceId)) {
          this.selectedInstanceIds.push(instanceId);
        }
      } else {
        this.selectedInstanceIds = this.selectedInstanceIds.filter(id => id !== instanceId);
      }
    },
    toggleSelectAll(isSelected) {
      if (isSelected) {
        this.selectedInstanceIds = this.device.instances.map(inst => inst.id);
      } else {
        this.selectedInstanceIds = [];
      }
    },
    batchUnlink() {
      if (this.selectedInstanceIds.length > 0) {
        this.$emit('batch-unmerge', this.selectedInstanceIds);
        this.isEditingInstances = false;
        this.selectedInstanceIds = [];
      }
    },
    isFirstOfType(instance) {
      if (!this.device.instances) return false;
      const isRecognized = instance.event_count === 0;
      const firstIndex = this.device.instances.findIndex(inst => {
        const instRecognized = inst.event_count === 0;
        return instRecognized === isRecognized;
      });
      const firstInst = this.device.instances[firstIndex];
      return firstInst ? firstInst.id === instance.id : false;
    }
  }
}
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
.bg-light-grey {
  background-color: #f5f5f5;
}
.border {
  border: 1px solid #e0e0e0;
}
</style>
