// added for WISPR-lab/data-export-gui
<template>
  <div class="pa-6">
    <!-- 1. Device Details Table (at the very top, transparent background) -->
    <div v-if="profileAttributesTable.length > 0" class="mb-6">
      <div class="text-subtitle-1 font-weight-medium text--primary mb-3">Device Details</div>
      <device-attributes-table :attributes="profileAttributesTable" />
    </div>

    <!-- 2. Name & Notes Inputs -->
    <div class="d-flex mb-6" style="gap: 36px;">
      <div style="flex: 0 0 auto; width: 300px;">
        <div class="text-subtitle-1 font-weight-medium text--primary">Name</div>
        
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
        <div class="text-subtitle-1 font-weight-medium text--primary">Notes</div>
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
          <span class="text-subtitle-1 font-weight-medium text--primary">Device Instances ({{ device.instances.length }})</span>
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
      <div v-if="isEditingInstances" class="d-flex align-center justify-space-between mb-4 pa-3 border rounded-lg bg-light-grey" style="gap: 8px; flex-wrap: wrap;">
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
        <div class="d-flex align-center" style="gap: 8px;">
          <v-btn
            color="primary"
            small
            outlined
            :disabled="selectedInstanceIds.length === 0"
            class="rounded-lg text-none"
            @click="moveSelected"
          >
            <v-icon left small>mdi-folder-move-outline</v-icon>
            Move to Existing Profile
          </v-btn>
          <v-btn
            color="primary"
            small
            outlined
            :disabled="selectedInstanceIds.length === 0"
            class="rounded-lg text-none"
            @click="createProfileWithSelected"
          >
            <v-icon left small>mdi-plus-box-outline</v-icon>
            Move to New Profile
          </v-btn>
        </div>
      </div>

      <div class="space-y-2" style="display: flex; flex-direction: column; gap: 12px;">
        <Instance
          v-for="inst in device.instances"
          :key="inst.id"
          :instance="inst"
          :show-checkbox="isEditingInstances"
          :selected="selectedInstanceIds.includes(inst.id)"
          :show-help="isFirstOfType(inst)"
          :ua-masking-text="uaMaskingText"
          @select="toggleInstanceSelection(inst.id, $event)"
          @showJSON="$emit('showJSON', $event)"
        />
      </div>
    </div>
    </div>
  </div>
</template>

<script>
import Instance from './Instance.vue';
import AttributesTable from './AttributesTable.vue';
import { getProfileRawAttrs } from '@/database/queries/devices_v2.js';
import { getCondensedModel } from '@/filters/GetCondensedModel.js';
import { getCondensedOS } from '@/filters/GetCondensedOS.js';
import { titleCase } from '@/filters/TitleCase.js';

export default {
  name: 'ProfileDropdown',
  components: {
    Instance,
    AttributesTable
  },
  props: {
    device: {
      type: Object,
      required: true
    },
    uaMaskingText: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      rawAttributes: {},
      isEditingInstances: false,
      selectedInstanceIds: []
    }
  },
  watch: {
    'device.id': {
      immediate: true,
      async handler(newId, oldId) {
        await this.loadAttributes();
        if (newId !== oldId) {
          this.selectedInstanceIds = [];
          this.isEditingInstances = false;
        }
      }
    },
    'device.instances': {
      handler(newVal, oldVal) {
        if (!oldVal || !newVal || newVal.length !== oldVal.length) {
          this.selectedInstanceIds = [];
          this.isEditingInstances = false;
        }
      }
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

      const uniqueIPs = [...new Set((this.device.instances || []).flatMap(function(inst) { return inst.client_ips || []; }))].filter(function(ip) {
        if (!ip) return false;
        const ipStr = String(ip).trim().toLowerCase();
        return ipStr !== '' && ipStr !== 'null' && ipStr !== 'none' && ipStr !== 'unknown' && ipStr !== 'undefined';
      });

      // Condense Manufacturer and Model into a single 'Model' value
      const modelValue = getCondensedModel(this.device.manufacturer, this.device.model);

      // Core attributes list (filtered to exclude empty / unknown values)
      const coreCandidates = [
        { label: 'Profile ID', value: this.device.id },
        { label: 'Model', value: modelValue },
        { label: 'OS', value: osValue },
        { label: 'First Active', value: this.device.first_seen, isTimestamp: true },
        { label: 'Last Active', value: this.device.last_seen, isTimestamp: true },
        { label: 'IP Addresses', value: uniqueIPs }
      ];

      const core = coreCandidates.filter(function(item) {
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
      const self = this;
      optionalKeys.forEach(function(opt) {
        const actualKey = Object.keys(self.rawAttributes).find(function(k) { return k.toLowerCase() === opt.key.toLowerCase(); });
        if (actualKey) {
          const val = self.rawAttributes[actualKey];
          if (val !== null && val !== undefined) {
            const valStr = String(val).trim();
            const lower = valStr.toLowerCase();
            if (valStr !== '' && lower !== 'unknown' && lower !== 'null' && lower !== 'none' && lower !== 'undefined') {
              if (!optionals.some(function(x) { return x.label === opt.label; })) {
                optionals.push({ label: opt.label, value: valStr });
              }
            }
          }
        }
      });

      return [].concat(core, optionals);
    }
  },
  methods: {
    async loadData() {
      await this.loadAttributes();
    },
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
        this.selectedInstanceIds = this.selectedInstanceIds.filter(function(id) { return id !== instanceId; });
      }
    },
    toggleSelectAll(isSelected) {
      if (isSelected) {
        this.selectedInstanceIds = this.device.instances.map(function(inst) { return inst.id; });
      } else {
        this.selectedInstanceIds = [];
      }
    },
    moveSelected() {
      if (this.selectedInstanceIds.length > 0) {
        this.$emit('move-instances', [...this.selectedInstanceIds]);
      }
    },
    createProfileWithSelected() {
      if (this.selectedInstanceIds.length > 0) {
        this.$emit('create-profile', [...this.selectedInstanceIds]);
      }
    },
    isFirstOfType(instance) {
      if (!this.device.instances) return false;
      const isRecognized = instance.event_count === 0;
      const firstIndex = this.device.instances.findIndex(function(inst) {
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
