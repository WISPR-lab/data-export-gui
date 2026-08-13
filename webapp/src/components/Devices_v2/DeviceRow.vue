// added for WISPR-lab/data-export-gui
<template>
  <v-expansion-panel
    active-class="grey lighten-5"
    class="device-row-panel"
  >
    <v-expansion-panel-header class="py-3 px-4">
      <template v-slot:default>
        <!-- Outer layout splits Avatar (left) from all content (right) to prevent under-avatar alignment bugs -->
        <div class="d-flex align-center w-100" style="min-width: 0;">
          
          <!-- Leftmost: Tag button & menu using shared TsEventTagMenu -->
          <div class="flex-shrink-0 mr-2" @click.stop>
            <ts-event-tag-menu
              :event="{ _id: deviceId, _source: { tags: localTags } }"
              :show-propagate-option="true"
              :event-count="eventCount"
              :events-query="eventsQuery"
              :persist="persistDeviceTags"
              silent
              @tag-added="handleTagAdded"
              @tag-removed="handleTagRemoved"
            />
          </div>

          <!-- Permanent Right Column: All text & buttons (groups content to align together) -->
          <div class="flex-grow-1 min-width-0">
            <v-row no-gutters align="center">
              
              <!-- Title & Badges block -->
              <v-col cols="12" md="6" class="pr-2 py-0.5">
                <div class="text-body-2 font-weight-medium text--primary" style="line-height: 1.3; min-width: 0;">
                  <!-- Tags rendered BEFORE title with right margin, matching EventList.vue -->
                  <ts-event-tags v-if="localTags.length > 0" :item="{ _source: { tags: localTags } }" class="mr-1.5" />

                  {{ capitalize(title) }}
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
                      :to="{ name: eventsRouteName, query: { chips: eventsChipsQuery } }"
                      @click.native.stop
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

    <v-expansion-panel-content class="transparent">
      <div class="pa-4">
        <div class="text-body-2 font-weight-medium text--secondary mb-3">{{ detailLabel }}</div>
        <attributes-table :attributes="displayAttributes" />
      </div>
    </v-expansion-panel-content>

    <!-- Confirmation Modal for Tag Propagation to Events -->
    <tag-propagate-modal
      v-model="showPropagateModal"
      :action="pendingTagAction.action"
      :tag="pendingTagAction.tag"
      :event-count="eventCount"
      @respond="handleModalResponse"
    />
  </v-expansion-panel>
</template>

<script>
import DB from '@/database/index.js';
import AttributesTable from '@/components/Devices_v2/AttributesTable.vue';
import TsEventTagMenu from '@/components/Events/EventTagMenu.vue';
import TsEventTags from '@/components/Events/EventTags.vue';
import TagPropagateModal from '@/components/Devices_v2/TagPropagateModal.vue';
import { capitalize } from '@/filters/Capitalize.js';

export default {
  name: 'DeviceRow',
  components: { AttributesTable, TsEventTags, TsEventTagMenu, TagPropagateModal },
  data() {
    return {
      localTags: Array.isArray(this.tags) ? this.tags.slice() : [],
      showPropagateModal: false,
      pendingTagAction: { action: 'add', tag: '' }
    };
  },
  props: {
    type:        { type: String,  default: 'record' },
    id:          { type: [String, Number], default: null },
    tags:        { type: Array,   default: function() { return []; } },
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
    groupRaw: { type: Object, default: function() { return {}; } }
  },
  watch: {
    // reset local tags when the source row is refetched, so remounts don't drop persisted tags
    tags(newVal) {
      this.localTags = Array.isArray(newVal) ? newVal.slice() : [];
    }
  },
  computed: {
    isRecord() {
      return this.type === 'record';
    },
    deviceId() {
      return this.isRecord ? this.id : (this.groupRaw && this.groupRaw.id) || null;
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
      return 'See ' + eventsText + ' in this event group';
    },
    activeDateLabel() {
      var fmt = this.$options.filters && this.$options.filters.dateRange;
      if (fmt) {
        if (this.firstSeen && this.lastSeen) {
          var range = fmt([this.firstSeen, this.lastSeen]);
          return range ? 'Active ' + range : this.fallbackDateStr;
        } else if (this.firstSeen) {
          var fDate = fmt([this.firstSeen, null]);
          return fDate ? 'First seen ' + fDate : this.fallbackDateStr;
        } else if (this.lastSeen) {
          var lDate = fmt([null, this.lastSeen]);
          return lDate ? 'Last seen ' + lDate : this.fallbackDateStr;
        }
      }
      return this.fallbackDateStr;
    },
    displayAttributes() {
      if (this.isRecord) return this.formattedAttributes;
      var attrs = [];
      var c = this.groupRaw;
      if (!c) return attrs;
      var parseList = function(val) {
        if (!val) return [];
        try {
          return typeof val === 'string' ? JSON.parse(val) : val;
        } catch (e) {
          return [];
        }
      };
      if (c.id) {
        attrs.push({ label: 'Device Group ID', value: c.id });
      }
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
    },
    eventsRouteName() {
      return this.$route.name === 'DemoDevices' ? 'DemoEvents' : 'Events';
    },
    eventsChipsQuery() {
      if (!this.eventsQuery) return '';
      if (this.eventsQuery.indexOf('client_session_id:') === 0) {
        var sid = this.eventsQuery.replace('client_session_id:', '').replace(/"/g, '');
        return 'client_session_id:' + sid;
      } else if (this.eventsQuery.indexOf('device_serial_number:') === 0) {
        var serial = this.eventsQuery.replace('device_serial_number:', '').replace(/"/g, '');
        return 'device_serial_number:' + serial;
      }
      return this.eventsQuery;
    }
  },
  methods: {
    capitalize,
    triggerInfoModal() {
      this.$emit('show-info', {
        title: 'Masked User Agent',
        description: 'To prevent browser fingerprinting, Apple devices (like iPhones running Mobile Safari) return simplified, generic user agent strings. This hides the specific device model details from websites and exports.'
      });
    },
    async persistDeviceTags(id, tags) {
      await DB.updateDeviceTags(this.type, id || this.deviceId, tags);
    },
    async handleTagAdded(tag) {
      if (tag && !this.localTags.includes(tag)) {
        this.localTags.push(tag);
      }
      await this.processTagAction('add', tag);
    },
    async handleTagRemoved(tag) {
      if (tag) {
        this.localTags = this.localTags.filter(t => t !== tag);
      }
      await this.processTagAction('remove', tag);
    },
    async processTagAction(action, tag) {
      // handles only the opt-in "also apply to matching events" propagation; the tag itself is already persisted by persistDeviceTags
      if (!tag || this.eventCount === 0 || !this.eventsQuery) return;
      var storageKey = action === 'add' ? 'takeout_tag_propagate_add' : 'takeout_tag_propagate_remove';
      var savedPref = localStorage.getItem(storageKey);

      if (savedPref === 'always') {
        await this.propagateToEvents(tag, action === 'remove');
      } else if (savedPref === 'never') {
        // device only
      } else {
        this.pendingTagAction = { action: action, tag: tag };
        this.showPropagateModal = true;
      }
    },
    async handleModalResponse({ propagate, dontAskAgain }) {
      var action = this.pendingTagAction.action;
      var tag = this.pendingTagAction.tag;
      var storageKey = action === 'add' ? 'takeout_tag_propagate_add' : 'takeout_tag_propagate_remove';

      if (dontAskAgain) {
        localStorage.setItem(storageKey, propagate ? 'always' : 'never');
      }

      if (propagate && this.eventsQuery) {
        await this.propagateToEvents(tag, action === 'remove');
      }
    },
    async propagateToEvents(tag, remove) {
      var changedCount = await DB.addTagToEventsQuery(this.eventsQuery, tag, remove);
      if (changedCount) {
        this.$store.dispatch('updateEventLabels', { label: tag, num: remove ? -changedCount : changedCount });
      }
    }
  }
};
</script>

<style scoped>
.border     { border: 1px solid #e0e0e0; }
.border-top { border-top: 1px solid #e0e0e0; }
.cursor-pointer { cursor: pointer; }
.device-row-panel {
  border: none !important;
  border-radius: 0 !important;
}
.device-row-panel > .v-expansion-panel-header {
  border-top: 1px solid #e0e0e0;
}
.device-row-panel:last-child {
  border-bottom: 1px solid #e0e0e0 !important;
}
.device-row-panel::before {
  box-shadow: none !important;
}
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
