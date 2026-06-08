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
      <div class="overline mb-3">Device Instances ({{ device.instances.length }})</div>
      <div class="space-y-2" style="display: flex; flex-direction: column; gap: 12px;">
        <DeviceInstance
          v-for="inst in device.instances"
          :key="inst.id"
          :instance="inst"
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
      rawAttributes: {}
    }
  },
  watch: {
    device: {
      immediate: true,
      handler: 'loadAttributes'
    }
  },
  computed: {
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
    }
  }
}
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
</style>
