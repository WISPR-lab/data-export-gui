// added for WISPR-lab/data-export-gui
<template>
  <v-container class="pa-6 white min-h-100" style="max-width: 1100px;">

    <div class="mb-6">
      <h1 class="text-h4 font-weight-bold text--primary mb-1">Devices (Mockup)</h1>
      <div class="text-body-2 text--secondary">Track account access records and detected device activity.</div>
    </div>

    <!-- Per-platform card -->
    <v-card
      v-for="(platform, platformIdx) in platforms"
      :key="'platform-' + platformIdx"
      outlined
      class="rounded-xl mb-6 shadow-sm overflow-hidden"
      style="background-color: white;"
    >
      <!-- Platform Header / Expansion Control -->
      <div 
        class="d-flex align-center justify-space-between pa-5 pb-3 cursor-pointer"
        @click="platform.collapsed = !platform.collapsed"
      >
        <div class="d-flex align-center min-width-0">
          <v-chip
            small
            :color="platform.color"
            class="white--text font-weight-bold mr-3 flex-shrink-0"
            style="height: 28px;"
          >
            <v-icon left size="16" color="white">{{ platform.icon }}</v-icon>
            {{ platform.displayName }}
          </v-chip>
          <div class="min-width-0">
            <h2 class="text-subtitle-1 font-weight-bold text--primary mb-0 text-truncate">
              {{ platform.accountLabel }}
            </h2>
          </div>
        </div>
        <v-btn icon>
          <v-icon>{{ platform.collapsed ? 'mdi-chevron-down' : 'mdi-chevron-up' }}</v-icon>
        </v-btn>
      </div>

      <!-- Collapsible area -->
      <v-slide-y-transition>
        <div v-show="!platform.collapsed">
          <!-- Tabs -->
          <v-tabs
            v-model="platform.activeTab"
            class="px-5 mt-1"
            color="primary"
            background-color="transparent"
            show-arrows
          >
            <v-tab class="text-body-2 font-weight-medium text-capitalize">
              Devices &amp; Sessions reported by {{ platform.displayName }} 
              <v-chip x-small class="ml-2" color="grey lighten-3" style="height: 18px;">
                {{ platform.totalGroundTruth }}
              </v-chip>
            </v-tab>
            <v-tab class="text-body-2 font-weight-medium text-capitalize">
              Additional Activity Clusters Inferred by LEStrADE
              <v-chip x-small class="ml-2" color="grey lighten-3" style="height: 18px;">
                {{ platform.clusters.length }}
              </v-chip>
            </v-tab>
          </v-tabs>

          <v-divider></v-divider>

          <v-tabs-items v-model="platform.activeTab" class="pa-5">

            <!-- TAB 1: Platform ground truth -->
            <v-tab-item>
              <!-- <div class="mb-4 d-flex align-center">
                <p class="text-body-2 text--secondary mb-0">
                  Records formatted directly from this data export. 
                </p></div> -->
              <div
                v-for="section in platform.sections"
                :key="section.key"
                v-if="section.entries.length"
                class="mb-8"
              >
                <!-- Section Header with Info Dialog Button instead of Subtitle -->
                <div class="d-flex align-center mb-3">
                  <h3 class="text-body-1 font-weight-bold text--primary mb-0 mr-2">{{ section.label }}</h3>
                  
                  <v-btn
                    v-if="section.description"
                    icon
                    x-small
                    color="blue darken-2"
                    @click.stop="openInfoModal(section.label, section.description)"
                  >
                    <v-icon size="16">mdi-information-outline</v-icon>
                  </v-btn>
                </div>

                <!-- Platform-inferred devices get a distinct "verified by platform" header -->
                <div v-if="section.key === 'platform_inferred_device'" class="mb-3">
                  <div class="platform-badge d-flex align-center pa-2 rounded-lg" style="gap: 6px;">
                    <v-icon size="14" color="blue darken-2">mdi-check-decagram</v-icon>
                    <span class="text-body-2 blue--text text--darken-2">
                      Reported directly by {{ platform.displayName }} — this is the platform's own device recognition.
                    </span>
                  </div>
                </div>

                <v-expansion-panels flat class="device-panels">
                  <v-expansion-panel
                    v-for="(entry, eIdx) in pageSlice(section)"
                    :key="section.key + '-' + eIdx"
                    class="mb-2 border rounded-xl overflow-hidden"
                  >
                    <v-expansion-panel-header class="pa-3">
                      <template v-slot:default>
                        <div class="d-flex align-center" style="gap: 10px; min-width: 0;">
                          <v-avatar size="34" color="grey lighten-5" class="flex-shrink-0">
                            <v-icon color="grey darken-3" size="17">{{ entry.icon }}</v-icon>
                          </v-avatar>
                          <div class="flex-grow-1 min-width-0">
                            <div class="d-flex flex-wrap align-center" style="gap: 6px;">
                              <span class="text-body-2 font-weight-medium text--primary">{{ entry.title }}</span>
                              <span v-if="entry.client_name" class="text-body-2 text--secondary">via {{ entry.client_name }}</span>
                              
                              <!-- Masked UA indicator -->
                              <v-chip
                                v-if="entry.is_reduced_ua"
                                color="grey lighten-2"
                                class="grey--text text--darken-3 px-2 text-body-2 font-weight-medium cursor-pointer"
                                style="height: 24px;"
                                @click.stop="openInfoModal('Masked User Agent', 'To prevent browser fingerprinting, Apple devices (like iPhones running Mobile Safari) return simplified, generic user agent strings. This hides the specific device model details from websites and exports.')"
                              >
                                Masked
                                <v-icon right size="14" class="grey--text text--darken-3">mdi-information-outline</v-icon>
                              </v-chip>
                              
                              <v-chip v-if="entry.has_passkey" color="success" outlined class="px-2 text-body-2" style="height: 24px;">Passkey</v-chip>
                            </div>
                            <div class="text-body-2 text--secondary mt-1 text-truncate">
                              <span>{{ [entry.firstSeen, entry.lastSeen] | dateRange }}</span>
                              <span v-if="entry.location"> • {{ entry.location }}</span>
                            </div>
                          </div>
                        </div>
                      </template>
                    </v-expansion-panel-header>

                    <v-expansion-panel-content class="grey lighten-5 border-top">
                      <div class="pa-3">
                        <div class="text-body-2 font-weight-medium text--secondary mb-2">{{ section.detailLabel }}</div>
                        <attributes-table :attributes="entry.formatted_attributes" />
                      </div>
                    </v-expansion-panel-content>
                  </v-expansion-panel>
                </v-expansion-panels>

                <!-- Pagination -->
                <div v-if="section.entries.length > PAGE_SIZE" class="d-flex align-center justify-center mt-1" style="gap: 6px;">
                  <v-btn icon x-small :disabled="section.page <= 1" @click="section.page -= 1">
                    <v-icon size="16">mdi-chevron-left</v-icon>
                  </v-btn>
                  <span class="text-body-2 text--secondary">
                    {{ section.page }} / {{ Math.ceil(section.entries.length / PAGE_SIZE) }}
                    <span class="grey--text text--darken-1 ml-1">({{ section.entries.length }} total)</span>
                  </span>
                  <v-btn icon x-small :disabled="section.page >= Math.ceil(section.entries.length / PAGE_SIZE)" @click="section.page += 1">
                    <v-icon size="16">mdi-chevron-right</v-icon>
                  </v-btn>
                </div>
              </div>

              <div
                v-if="!platform.sections.some(function(s) { return s.entries.length > 0; })"
                class="text-body-2 text--secondary italic pa-6 text-center grey lighten-5 rounded-xl"
              >
                No platform records found for this account.
              </div>
            </v-tab-item>

            <!-- TAB 2: Detected Devices (our inference) -->
            <v-tab-item>
              <div class="mb-4 d-flex align-center">
                <p class="text-body-2 text--secondary mb-0">
                  LEStrADE's analysis of events originating different devices. We grouped logins that appear to come from the same device based on browser, OS, and timing patterns. 
                  This is a <b>conservative</b> estimate: multiple clusters here may actually come from the same device.
                </p>
              </div>

              <div v-if="!platform.clusters.length"
                class="text-body-2 text--secondary italic pa-6 text-center grey lighten-5 rounded-xl">
                No device clusters detected for this account.
              </div>

              <div v-else>
                <div
                  v-for="(cluster, cIdx) in clusterPageSlice(platform)"
                  :key="'cluster-' + cIdx"
                  class="cluster-row d-flex align-center justify-space-between pa-3 mb-2 rounded-xl border"
                  style="gap: 10px;"
                >
                  <div class="d-flex align-center flex-grow-1 min-width-0" style="gap: 10px;">
                    <v-avatar size="34" color="grey lighten-5" class="flex-shrink-0">
                      <v-icon color="grey darken-3" size="17">mdi-monitor-cellphone</v-icon>
                    </v-avatar>
                    <div class="min-width-0">
                      <div class="text-body-2 font-weight-medium text--primary text-truncate">{{ cluster.title }}</div>
                      <div class="text-body-2 text--secondary">
                        <span v-if="cluster.norm_client">{{ cluster.norm_client }} · </span>
                        {{ cluster.dateString }}
                      </div>
                    </div>
                  </div>
                  <span v-if="cluster.event_count" class="text-body-2 text--secondary flex-shrink-0">{{ cluster.event_count }} events</span>
                </div>

                <div v-if="platform.clusters.length > PAGE_SIZE" class="d-flex align-center justify-center mt-2" style="gap: 6px;">
                  <v-btn icon x-small :disabled="platform.clusterPage <= 1" @click="platform.clusterPage -= 1">
                    <v-icon size="16">mdi-chevron-left</v-icon>
                  </v-btn>
                  <span class="text-body-2 text--secondary">
                    {{ platform.clusterPage }} / {{ Math.ceil(platform.clusters.length / PAGE_SIZE) }}
                    <span class="grey--text text--darken-1 ml-1">({{ platform.clusters.length }} total)</span>
                  </span>
                  <v-btn icon x-small :disabled="platform.clusterPage >= Math.ceil(platform.clusters.length / PAGE_SIZE)" @click="platform.clusterPage += 1">
                    <v-icon size="16">mdi-chevron-right</v-icon>
                  </v-btn>
                </div>
              </div>
            </v-tab-item>

          </v-tabs-items>
        </div>
      </v-slide-y-transition>
    </v-card>

    <!-- General Info Modal Dialog -->
    <v-dialog v-model="infoModal.open" max-width="500">
      <v-card class="pa-4 rounded-xl">
        <v-card-title class="text-h6 font-weight-bold text--primary pb-2 pt-1 px-4">
          {{ infoModal.title }}
        </v-card-title>
        <v-card-text class="text-body-1 text--secondary px-4 py-2" style="line-height: 1.6;">
          {{ infoModal.description }}
        </v-card-text>
        <v-card-actions class="justify-end pt-3 pb-1 px-4">
          <v-btn color="primary" text class="text-capitalize" @click="infoModal.open = false">
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

  </v-container>
</template>

<script>
import AttributesTable from '@/components/Devices/AttributesTable.vue';
import { getResolvedSessionsRegistrations } from '@/database/queries/resolved_sessions_registrations.js';
import { getUnlinkedClusters } from '@/database/queries/instances_v2.js';
import { getDB } from '@/database/index.js';
import { hexColor } from '@/utils/hex.js';

export default {
  name: 'DevicesMockup',
  components: { AttributesTable },
  data() {
    return {
      platforms: [],
      PAGE_SIZE: 5,
      infoModal: {
        open: false,
        title: '',
        description: ''
      }
    };
  },
  mounted() {
    this.fetchLiveData();
  },
  methods: {
    pageSlice(section) {
      var start = (section.page - 1) * this.PAGE_SIZE;
      return section.entries.slice(start, start + this.PAGE_SIZE);
    },
    clusterPageSlice(platform) {
      var start = (platform.clusterPage - 1) * this.PAGE_SIZE;
      return platform.clusters.slice(start, start + this.PAGE_SIZE);
    },
    openInfoModal(title, description) {
      this.infoModal.title = title;
      this.infoModal.description = description;
      this.infoModal.open = true;
    },
    async fetchLiveData() {
      try {
        var db = await getDB();

        var uploads = await db.exec('SELECT * FROM uploads', {
          returnValue: 'resultRows',
          rowMode: 'object'
        });

        var states = await getResolvedSessionsRegistrations();
        var allClusters = await getUnlinkedClusters();

        var platformMeta = {
          facebook:  { displayName: 'Facebook',    icon: 'mdi-facebook',  color: '#5E75C2' },
          google:    { displayName: 'Google',       icon: 'mdi-google',    color: '#FD7EAC' },
          apple:     { displayName: 'Apple/iCloud', icon: 'mdi-apple',     color: '#000000' },
          discord:   { displayName: 'Discord',      icon: 'mdi-discord',   color: '#5865F2' },
          instagram: { displayName: 'Instagram',    icon: 'mdi-instagram', color: '#E1306C' }
        };

        var entityIcons = {
          session:                  'mdi-cookie-outline',
          app_registration:         'mdi-cellphone-link',
          hardware_registration:    'mdi-cellphone',
          platform_inferred_device: 'mdi-check-decagram-outline'
        };

        var sectionDefs = [
          {
            key: 'session',
            label: 'Session History',
            description: 'Each entry is one recorded login session. Many platforms assigns a unique ID to every session, so you might see multiple sessions that all came from the same phone or computer.',
            detailLabel: 'Details',
            sortByGroup: true
          },
          {
            key: 'app_registration',
            label: 'Registered Mobile Apps',
            description: 'Records of the individual mobile apps that are registered with the platform. Each app installation typically gets assigned a unique ID from the platform, which may be used for advertising or for sending push notifications. These likely overlap with any logged-in sessions: you may have a phone with a registered app, and that same phone may have multiple sessions logged over time.', 
            detailLabel: 'Details',
            sortByGroup: false
          },
          {
            key: 'hardware_registration',
            label: 'Registered Hardware',
            description: 'Physical devices that are connected to this account at the operating-system level. This typically includes Apple devices that are registered with a specific iCloud account, and Android devices that are registered with a Google account. These records often include a unique hardware identifier like a serial number or an IMEI.',
            detailLabel: 'Details',
            sortByGroup: false
          },
          {
            key: 'platform_inferred_device',
            label: 'Devices Recognized by the Platform',
            description: 'This is a list of the unique devices that the platform claims to directly recognize based on their own internal server-side algorithms (cookies, persistent IDs, fingerprinting, etc). ',
            detailLabel: 'Attributes',
            sortByGroup: false
          }
        ];

        var TIMESTAMP_KEYS = ['entity_first_seen_timestamp', 'entity_last_seen_timestamp', 'timestamp'];

        this.platforms = uploads.map(function(upload) {
          var platformKey = (upload.platform || '').toLowerCase();
          var meta = platformMeta[platformKey] || { displayName: upload.platform, icon: 'mdi-account', color: '#757575' };
          
          // Use upload.color (database color) formatted with hexColor, otherwise fallback to brand meta.color
          var dbColor = upload.color ? hexColor(upload.color) : null;
          var displayColor = dbColor ? dbColor : meta.color;

          var uploadEntries = states
            .filter(function(s) { return s.upload_id === upload.id; })
            .map(function(s) {
              var firstSeen = s.attributes.entity_first_seen_timestamp || null;
              var lastSeen  = s.attributes.entity_last_seen_timestamp  || null;
              var location  = s.attributes.location || s.attributes.device_last_location || '';

              var formattedAttrs = Object.entries(s.attributes)
                .filter(function(pair) { return !pair[0].startsWith('norm__') && pair[1] !== null && pair[1] !== ''; })
                .map(function(pair) {
                  var k = pair[0]; var v = pair[1];
                  return {
                    label: k.replace(/_/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); }),
                    value: typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v),
                    isTimestamp: TIMESTAMP_KEYS.indexOf(k) !== -1
                  };
                });

              return {
                id: s.id,
                entity_type: s.entity_type,
                instance_id: s.instance_id || null,
                title: s.model_name,
                client_name: s.client_name,
                icon: entityIcons[s.entity_type] || 'mdi-devices',
                firstSeen: firstSeen,
                lastSeen: lastSeen,
                location: location,
                is_reduced_ua: s.is_reduced_ua,
                has_trusted_cookie: s.has_trusted_cookie,
                has_passkey: s.has_passkey,
                event_count: s.event_count,
                events_query: s.events_query,
                formatted_attributes: formattedAttrs
              };
            });

          var sections = sectionDefs.map(function(def) {
            var entries = uploadEntries.filter(function(e) { return e.entity_type === def.key; });

            if (def.sortByGroup) {
              var instMax = {};
              entries.forEach(function(e) {
                if (!e.instance_id) return;
                if (!instMax[e.instance_id] || e.lastSeen > instMax[e.instance_id]) {
                  instMax[e.instance_id] = e.lastSeen || '';
                }
              });
              entries = entries.slice().sort(function(a, b) {
                var aKey = a.instance_id ? (instMax[a.instance_id] || '') : (a.lastSeen || '');
                var bKey = b.instance_id ? (instMax[b.instance_id] || '') : (b.lastSeen || '');
                if (aKey !== bKey) return aKey < bKey ? 1 : -1;
                var aL = a.lastSeen || ''; var bL = b.lastSeen || '';
                return aL < bL ? 1 : aL > bL ? -1 : 0;
              });
            } else {
              entries = entries.slice().sort(function(a, b) {
                var aL = a.lastSeen || ''; var bL = b.lastSeen || '';
                if (!aL && !bL) return 0;
                if (!aL) return 1;
                if (!bL) return -1;
                return aL < bL ? 1 : aL > bL ? -1 : 0;
              });
            }

            return { key: def.key, label: def.label, description: def.description, detailLabel: def.detailLabel, entries: entries, page: 1 };
          });

          var totalGroundTruth = sections.reduce(function(sum, s) { return sum + s.entries.length; }, 0);
          var uploadClusters = allClusters.filter(function(c) { return c.upload_id === upload.id; });

          return {
            displayName: meta.displayName,
            accountLabel: upload.given_name || 'Primary Account',
            icon: meta.icon,
            color: displayColor,
            sections: sections,
            totalGroundTruth: totalGroundTruth,
            clusters: uploadClusters,
            clusterPage: 1,
            activeTab: 0,
            collapsed: false
          };
        });

      } catch (err) {
        console.error('Error fetching live DB data for mockup:', err);
      }
    }
  }
};
</script>

<style scoped>
.min-h-100 { min-height: 100vh; }
.border { border: 1px solid #e0e0e0; }
.border-top { border-top: 1px solid #e0e0e0; }
.shadow-sm { box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.1); }
.platform-badge {
  background-color: #e3f2fd;
  border: 1px solid #90caf9;
}
.cluster-row {
  background-color: #fafafa;
  transition: background-color 0.15s ease;
}
.cluster-row:hover { background-color: #f0f0f0; }
.cursor-pointer {
  cursor: pointer;
}
</style>
