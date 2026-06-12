// added for WISPR-lab/data-export-gui
<template>
  <div class="pa-6">
    <!-- 1. Device Details Table (at the very top, transparent background) -->
    <div v-if="profileAttributesTable.length > 0" class="mb-6">
      <div class="overline mb-3">Device Details</div>
      <v-simple-table dense class="transparent">
        <template v-slot:default>
          <tbody>
            <tr v-for="attr in profileAttributesTable" :key="attr.label">
              <td style="font-weight: 600; width: 200px; color: #424242;">{{ attr.label }}</td>
              <td style="word-break: break-word;">
                <template v-if="attr.isTimestamp">
                  {{ attr.value | longDateTimeLocal }}
                </template>
                <template v-else>
                  {{ attr.value | formatDeviceDetails }}
                </template>
              </td>
            </tr>
          </tbody>
        </template>
      </v-simple-table>
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
          :placeholder="isGeneric ? 'Add any personal notes about this record.' : 'Add any personal notes about this device.'"
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

    <!-- Optional Help Footer for Generic Records -->
    <div v-if="isGeneric" class="mt-6 pt-4">
      <p class="body-2 grey--text text--darken-3 mb-0">
        <v-icon small class="mr-1" color="grey--darken-3">mdi-information-outline</v-icon>
        To group this record, drag this card onto one of your confirmed devices above.
      </p>
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
import { getProfileAttributes } from '@/database/queries/devices_v2.js';

export default {
  name: 'DeviceProfileDropdown',
  components: {
    DeviceInstance
  },
  props: {
    device: {
      type: Object,
      required: true
    },
    isGeneric: {
      type: Boolean,
      default: false
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
      // Construct OS field (e.g. iOS 15.7 -> 16.2)
      const osName = this.device.latest_os_name || this.device.os_name || this.device.latest_os_type || this.device.os_type || '';
      const versions = (this.device.all_os_versions || []).filter(Boolean);
      let osValue = '';
      if (osName) {
        osValue = osName.toUpperCase();
        if (versions.length > 0) {
          versions.sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));
          const firstV = versions[0];
          const lastV = versions[versions.length - 1];
          if (firstV === lastV) {
            osValue = `${osName.toUpperCase()} ${firstV}`;
          } else {
            osValue = `${osName.toUpperCase()} ${firstV} → ${lastV}`;
          }
        }
      }

      const uniqueIPs = [...new Set((this.device.instances || []).flatMap(inst => inst.ip_addresses || []))].filter(Boolean);

      // Condense Manufacturer and Model into a single 'Model' value
      let modelValue = '';
      const mfr = (this.device.manufacturer || '').trim();
      const mdl = (this.device.model || '').trim();
      if (mfr && mdl) {
        if (mdl.toLowerCase().startsWith(mfr.toLowerCase())) {
          modelValue = mdl;
        } else {
          modelValue = `${mfr} ${mdl}`;
        }
      } else {
        modelValue = mdl || mfr || '';
      }

      // Core attributes list (filtered to exclude empty / unknown values)
      const coreCandidates = [
        { label: 'Model', value: modelValue },
        { label: 'OS', value: osValue },
        { label: 'First Active', value: this.device.first_seen, isTimestamp: true },
        { label: 'Last Active', value: this.device.last_seen, isTimestamp: true },
        { label: 'IP Addresses', value: uniqueIPs.length > 0 ? uniqueIPs.join(', ') : '' }
      ];

      const core = coreCandidates.filter(item => item.value !== null && item.value !== undefined && String(item.value).trim() && String(item.value).toLowerCase() !== 'unknown');

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
          if (val && String(val).trim() && String(val).toLowerCase() !== 'unknown') {
            if (!optionals.some(x => x.label === opt.label)) {
              optionals.push({ label: opt.label, value: String(val).trim() });
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
          this.rawAttributes = await getProfileAttributes(this.device.id);
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
