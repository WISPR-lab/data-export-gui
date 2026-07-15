// added for WISPR-lab/data-export-gui
<template>
  <v-expansion-panel
    class="mb-2 border rounded-xl overflow-hidden"
  >
    <v-expansion-panel-header class="py-3 px-4">
      <template v-slot:default>
        <!-- Outer layout splits Avatar (left) from all content (right) to prevent under-avatar alignment bugs -->
        <div class="d-flex align-center w-100" style="min-width: 0;">
          
          <!-- Permanent Left Column: Avatar Logo (resists wrapping) -->
          <div class="flex-shrink-0 mr-3">
            <!-- <v-avatar size="36" color="grey lighten-4">
              <v-icon color="grey darken-2" size="18">{{ icon }}</v-icon>
            </v-avatar> -->
          </div>

          <!-- Permanent Right Column: All text & buttons (groups content to align together) -->
          <div class="flex-grow-1 min-width-0">
            <v-row no-gutters align="center">
              
              <!-- Title & Badges block -->
              <v-col cols="12" md="6" class="pr-2 py-0.5">
                <div class="text-body-2 font-weight-medium text--primary" style="line-height: 1.3; min-width: 0;">
                  {{ titleCase(title) }}
                  <span v-if="clientName" class="text-body-2 text--secondary font-weight-regular ml-1">via {{ clientName }}</span>
                  
                  <!-- Inline Masked link -->
                  <span
                    v-if="isReducedUa"
                    class="masked-glossary ml-2"
                    @click.stop="triggerInfoModal"
                  >
                    <v-icon size="13" class="icon-target">mdi-fingerprint-off</v-icon>
                    Masked
                  </span>

                  <!-- Inline Passkey chip -->
                  <v-chip
                    v-if="isRecord && hasPasskey"
                    color="success"
                    outlined
                    x-small
                    class="ml-2 px-1.5"
                    style="height: 18px;"
                  >
                    Passkey
                  </v-chip>
                </div>
              </v-col>

              <!-- Active Date Label (grows to md="6" if there is no events action button) -->
              <v-col cols="12" :md="eventsQuery ? 4 : 6" class="text-body-2 text--secondary pr-2 py-0.5 mt-1 mt-md-0">
                {{ activeDateLabel }}
              </v-col>

              <!-- Events Action Button (hidden entirely when eventsQuery is empty) -->
              <v-col v-if="eventsQuery" cols="12" md="2" class="py-0.5 mt-1 mt-md-0">
                <v-tooltip bottom>
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn
                      v-bind="attrs"
                      v-on="on"
                      x-small
                      text
                      color="primary"
                      class="text-capitalize pa-0"
                      style="font-size: 12px; font-weight: 500; height: auto;"
                      @click.stop="goToEvents"
                    >
                      {{ buttonText }}
                      <v-icon right size="13" class="ml-1">mdi-arrow-right</v-icon>
                    </v-btn>
                  </template>
                  <span>{{ buttonTooltip }}</span>
                </v-tooltip>
              </v-col>

            </v-row>
          </div>

        </div>
      </template>
    </v-expansion-panel-header>

    <v-expansion-panel-content class="grey lighten-5 border-top">
      <div class="pa-4">
        <div class="text-body-2 font-weight-medium text--secondary mb-3">{{ detailLabel }}</div>
        <attributes-table :attributes="displayAttributes" />
      </div>
    </v-expansion-panel-content>
  </v-expansion-panel>
</template>

<script>
import AttributesTable from '@/components/Devices/AttributesTable.vue';
import { titleCase } from '@/filters/TitleCase.js';

export default {
  name: 'DeviceRow',
  components: { AttributesTable },
  props: {
    type:        { type: String,  default: 'record' },
    title:       { type: String,  default: 'Unknown Device' },
    clientName:  { type: String,  default: '' },
    icon:        { type: String,  default: 'mdi-devices' },
    firstSeen:   { type: [String, Number], default: null },
    lastSeen:    { type: [String, Number], default: null },
    fallbackDateStr: { type: String, default: '' },
    eventsQuery: { type: String,  default: '' },
    isReducedUa:         { type: Boolean, default: false },
    hasPasskey:          { type: Boolean, default: false },
    detailLabel:         { type: String,  default: 'Details' },
    formattedAttributes: { type: Array,    default: function() { return []; } },
    eventCount: { type: Number, default: 0 },
    clusterRaw: { type: Object, default: function() { return {}; } }
  },
  computed: {
    isRecord() {
      return this.type === 'record';
    },
    buttonText() {
      var count = this.eventCount;
      if (count && count > 0) {
        return count + (count === 1 ? ' event' : ' events');
      }
      return 'Events';
    },
    buttonTooltip() {
      var count = this.eventCount || 0;
      var eventsText = count + (count === 1 ? ' event' : ' events');
      if (this.isRecord) {
        return 'See ' + eventsText + ' with this session ID';
      }
      return 'See ' + eventsText + ' in this activity cluster';
    },
    activeDateLabel() {
      var fmt = this.$options.filters && this.$options.filters.dateRange;
      if (fmt) {
        var normalize = function(val) {
          if (val === null || val === undefined || val === '') return null;
          var num = Number(val);
          if (!isNaN(num)) {
            if (num < 10000000000) return num * 1000;
            return num;
          }
          return val;
        };
        var range = fmt([normalize(this.firstSeen), normalize(this.lastSeen)]);
        return range ? 'Active ' + range : this.fallbackDateStr;
      }
      return this.fallbackDateStr;
    },
    displayAttributes() {
      if (this.isRecord) return this.formattedAttributes;
      var attrs = [];
      var c = this.clusterRaw;
      if (!c) return attrs;
      var parseList = function(val) {
        if (!val) return [];
        try {
          return typeof val === 'string' ? JSON.parse(val) : val;
        } catch (e) {
          return [];
        }
      };
      if (c.latest_client_ip) {
        attrs.push({ label: 'Latest Client IP', value: c.latest_client_ip });
      }
      var ips = parseList(c.client_ips);
      if (ips.length > 0) {
        attrs.push({ label: 'All Detected IPs', value: ips });
      }
      var locations = parseList(c.locations);
      if (locations.length > 0) {
        attrs.push({ label: 'Locations', value: locations });
      }
      var osList = parseList(c.os_versions);
      if (osList.length > 0) {
        attrs.push({ label: 'OS Versions', value: osList });
      }
      var clientList = parseList(c.client_versions);
      if (clientList.length > 0) {
        attrs.push({ label: 'Client Versions', value: clientList });
      }
      if (c.latest_os_version) {
        attrs.push({ label: 'Latest OS Version', value: c.latest_os_version });
      }
      if (c.latest_client_version) {
        attrs.push({ label: 'Latest Client Version', value: c.latest_client_version });
      }
      return attrs;
    }
  },
  methods: {
    titleCase,
    triggerInfoModal() {
      this.$emit('show-info', {
        title: 'Masked User Agent',
        description: 'To prevent browser fingerprinting, Apple devices (like iPhones running Mobile Safari) return simplified, generic user agent strings. This hides the specific device model details from websites and exports.'
      });
    },
    goToEvents() {
      var routeName = this.$route.name === 'DemoDevices' ? 'DemoEvents' : 'Events';
      this.$router.push({ name: routeName, query: { q: this.eventsQuery } }).catch(function() {});
    }
  }
};
</script>

<style scoped>
.border     { border: 1px solid #e0e0e0; }
.border-top { border-top: 1px solid #e0e0e0; }
.cursor-pointer { cursor: pointer; }
.masked-glossary {
  display: inline-flex;
  align-items: center;
  color: #616161;
  border-bottom: 1px dotted #757575;
  cursor: help;
  transition: all 0.15s ease;
  line-height: 1.1;
  font-size: 11px;
}
.masked-glossary .icon-target {
  color: #616161 !important;
  margin-right: 4px;
}
.masked-glossary:hover {
  color: #212121;
  border-bottom-style: solid;
}
.w-100 {
  width: 100%;
}
</style>
