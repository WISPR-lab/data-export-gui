// added for WISPR-lab/data-export-gui
<template>
  <v-card 
    outlined 
    :ripple="false"
    class="pa-0 d-flex flex-column cursor-pointer" 
    style="background-color: white;"
    @click="expanded = !expanded"
  >
    <div class="pa-4 d-flex align-center" style="gap: 16px; width: 100%;">
      <!-- Selection Checkbox (Edit mode) -->
      <v-checkbox
        v-if="showCheckbox"
        :input-value="selected"
        hide-details
        class="ma-0 pa-0 flex-shrink-0"
        @change="$emit('select', $event)"
        @click.native.stop
      ></v-checkbox>

      <!-- UA summary chip column -->
      <div v-if="instance.ua_summary && !instance.ua_summary.isUnknown" class="d-flex align-center" style="flex: 0 0 120px; max-width: 120px; width: 120px;">
        <UASummaryChip
          :summary="instance.ua_summary"
          style="max-width: 100%; height: auto;"
          class="align-start ma-0"
        />
      </div>

      <!-- OS & Timeline -->
      <div class="flex-grow-1 text-truncate">
        <div class="text-body-2 font-weight-medium text--primary d-flex align-center">
          <span>{{ getHeaderLabel }}</span>
          <v-tooltip v-if="isMaskedInstance" bottom max-width="320">
            <template v-slot:activator="{ on, attrs }">
              <span
                class="d-inline-flex align-center justify-center rounded-circle grey lighten-2 ml-2"
                style="width: 20px; height: 20px; flex-shrink: 0;"
                v-bind="attrs"
                v-on="on"
              >
                <v-icon
                  color="grey darken-3"
                  style="font-size: 13px;"
                >
                  mdi-fingerprint-off
                </v-icon>
              </span>
            </template>
            <span>{{ computedMaskingText }}</span>
          </v-tooltip>
        </div>
        <div class="text-body-2 text--secondary">
          <span v-if="getOSLabel">{{ getOSLabel }}</span>
          <span v-if="getTimelineString && getOSLabel" class="ml-2 mr-2">&bull;</span>
          <span v-if="getTimelineString">Active {{ getTimelineString }}</span>
        </div>
      </div>
      <!-- Actions -->
      <div class="d-flex align-center flex-shrink-0" style="gap: 8px;">
        <v-btn
          v-if="instance.event_count > 0"
          text
          small
          color="primary"
          @click.stop="goToExplore"
          title="View events for this instance"
        >
          {{ instance.event_count }} Events
          <v-icon right small>mdi-arrow-right</v-icon>
        </v-btn>

        <v-btn icon small @click.stop="expanded = !expanded">
          <v-icon>{{ expanded ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
        </v-btn>
      </div>
    </div>

    <!-- Expanded Content -->
    <v-expand-transition>
      <div v-if="expanded" class="px-4 pb-4 pt-0" @click.stop>
        <v-divider class="mb-4"></v-divider>
        <device-attributes-table :attributes="instance.formatted_attributes" />
      </div>
    </v-expand-transition>
  </v-card>
</template>

<script>
import UASummaryChip from './UASummaryChip.vue';
import DeviceAttributesTable from './DeviceAttributesTable.vue';
import { titleCase } from '@/filters/TitleCase.js';

export default {
  name: 'DeviceInstance',
  components: { UASummaryChip, DeviceAttributesTable },
  props: {
    instance: {
      type: Object,
      required: true
    },
    showCheckbox: {
      type: Boolean,
      default: false
    },
    selected: {
      type: Boolean,
      default: false
    },
    showHelp: {
      type: Boolean,
      default: false
    },
    uaMaskingText: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      expanded: false
    };
  },
  computed: {
    computedMaskingText() {
      if (!this.uaMaskingText) return '';
      const os = (this.instance.os_name || '').trim().toLowerCase();
      const model = (this.instance.model || '').trim().toLowerCase();
      const isMac = os === 'macos' || model === 'macintosh';
      const baseText = isMac ? this.uaMaskingText.mac_ipad : this.uaMaskingText.iphone;
      if (!baseText) return '';
      return baseText.split('.')[0] + '.';
    },
    isMaskedInstance() {
      if (this.instance.apple_masking && this.instance.apple_masking !== '0' && this.instance.apple_masking !== 'false') return true;
      const model = (this.instance.model || '').trim().toLowerCase();
      return model === 'iphone' || model === 'ipad' || model === 'ipod' || model === 'macintosh' || model === 'generic';
    },
    getHeaderLabel() {
      const type = this.instance.instance_source_type;
      
      const getStreamStr = () => {
        const sum = this.instance.ua_summary;
        if (sum) {
          const p = sum.primary || '';
          const s = sum.secondary || '';
          const fmt = s ? `${p} (${s})` : p;
          if (fmt) return `Session from ${fmt}`;
        }
        return 'Session';
      };

      if (type === 'raw_devices') {
        return 'Recognized Device';
      } else if (type === 'both') {
        return `Recognized Device; ${getStreamStr()}`;
      } else {
        return getStreamStr();
      }
    },
    getClientLabel() {
      const name = this.instance.client_name || 'Unknown Client';
      if (this.instance.latest_client_version) {
        return `${name} (v${this.instance.latest_client_version})`;
      }
      return name;
    },
    getOSLabel() {
      const os = this.instance.os_type || this.instance.os_name || 'Unknown OS';
      if (this.instance.latest_os_version) {
        return `${titleCase(os)} ${this.instance.latest_os_version}`;
      }
      return titleCase(os);
    },
    getTimelineString() {
      if (!this.instance.first_seen || !this.instance.last_seen) return '';
      const start = new Date(this.instance.first_seen * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
      const end = new Date(this.instance.last_seen * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
      return start === end ? start : `${start} – ${end}`;
    }
  },
  methods: {
    goToExplore() {
      const queryString = `device_instance_id:${this.instance.id}`;
      const routeName = this.$route.name === 'DemoDevices' ? 'DemoExplore' : 'Explore';
      this.$router.push({
        name: routeName,
        query: { q: queryString }
      });
    }
  }
}
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
</style>
