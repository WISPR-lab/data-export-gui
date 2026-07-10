// added for WISPR-lab/data-export-gui
<template>
  <v-container class="pa-6 white min-h-100" style="max-width: 1200px;">

    <!-- Page Header -->
    <div class="mb-6">
      <h1 class="text-h4 font-weight-bold text--primary mb-1">Devices (Mockup)</h1>
      <div class="text-body-2 text--secondary">Track account access records and unlinked activity clusters.</div>
    </div>

    <!-- Generic Platform Loop -->
    <v-card
      v-for="(platform, platformIdx) in platforms"
      :key="'platform-' + platformIdx"
      outlined
      class="pa-5 rounded-xl mb-6 shadow-sm"
      style="background-color: white;"
    >
      <!-- Platform Header -->
      <div class="d-flex align-center mb-5">
        <v-avatar size="44" :color="platform.color" class="mr-3">
          <v-icon color="white" size="26">{{ platform.icon }}</v-icon>
        </v-avatar>
        <div>
          <h2 class="text-subtitle-1 font-weight-bold text--primary mb-0">{{ platform.displayName }} Account</h2>
          <div class="text-body-2 text--secondary">{{ platform.accountLabel }}</div>
        </div>
      </div>

      <!-- Section loop — one block per entity type -->
      <div
        v-for="section in platform.sections"
        :key="section.key"
        v-if="section.entries.length"
        class="mb-8"
      >
        <h3 class="text-body-1 font-weight-bold text--primary mb-1">{{ section.label }}</h3>
        <p class="text-body-2 text--secondary mb-3">{{ section.description }}</p>

        <!-- Cards for current page -->
        <v-expansion-panels flat class="device-panels">
          <v-expansion-panel
            v-for="(entry, eIdx) in pageSlice(section)"
            :key="section.key + '-' + eIdx"
            class="mb-3 border rounded-xl overflow-hidden device-profile-card"
          >
            <v-expansion-panel-header class="pa-4">
              <template v-slot:default="{ open }">
                <div class="device-header-row py-1 d-flex align-center justify-space-between w-100" style="gap: 12px;">
                  <div class="d-flex align-center flex-grow-1 min-width-0">
                    <v-avatar size="40" color="grey lighten-5" class="mr-4 flex-shrink-0">
                      <v-icon color="grey darken-3" size="20">{{ entry.icon }}</v-icon>
                    </v-avatar>

                    <div class="d-flex flex-column min-width-0">
                      <div class="d-flex flex-wrap align-center">
                        <span class="text-body-2 font-weight-medium text--primary">{{ entry.title }}</span>
                        <span v-if="entry.client_name" class="text-body-2 text--secondary ml-2">
                          via {{ entry.client_name }}
                        </span>
                        <!-- Masked UA chip — inline after client name -->
                        <v-tooltip v-if="entry.is_reduced_ua" bottom max-width="320">
                          <template v-slot:activator="{ on, attrs }">
                            <v-chip
                              small
                              color="grey lighten-2"
                              class="font-weight-medium flex-shrink-0 grey--text text--darken-3 px-2 ml-2"
                              style="height: 20px;"
                              v-bind="attrs"
                              v-on="on"
                            >
                              <v-icon left x-small class="grey--text text--darken-3" style="margin-right: 3px;">mdi-fingerprint-off</v-icon>
                              Masked
                            </v-chip>
                          </template>
                          <span>To prevent fingerprinting, browsers on iPhones use generic User-Agents that hide the exact model.</span>
                        </v-tooltip>
                        <!-- Passkey chip -->
                        <v-chip v-if="entry.has_passkey" small color="success" outlined class="px-2 ml-2" style="height: 20px;">
                          Passkey
                        </v-chip>
                      </div>
                      <div class="text-body-2 text--secondary mt-1 text-truncate">
                        <span>{{ [entry.firstSeen, entry.lastSeen] | dateRange }}</span>
                        <span v-if="entry.location"> • {{ entry.location }}</span>
                      </div>
                    </div>
                  </div>

                  <!-- Right Side: commented-out Events button placeholder -->
                  <div class="mr-4 flex-shrink-0">
                    <!-- <v-btn v-if="entry.event_count" text small color="primary" ... /> -->
                  </div>
                </div>
              </template>
            </v-expansion-panel-header>

            <v-expansion-panel-content class="grey lighten-5 border-top">
              <div class="pa-4">
                <div class="text-body-2 font-weight-medium text--secondary mb-2">{{ section.detailLabel }}</div>
                <attributes-table :attributes="entry.formatted_attributes" />
              </div>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>

        <!-- Pagination bar — only shown when total > PAGE_SIZE -->
        <div v-if="section.entries.length > PAGE_SIZE" class="d-flex align-center justify-center mt-2" style="gap: 8px;">
          <v-btn
            icon
            x-small
            :disabled="section.page <= 1"
            @click="section.page -= 1"
          >
            <v-icon size="18">mdi-chevron-left</v-icon>
          </v-btn>
          <span class="text-body-2 text--secondary">
            {{ section.page }} / {{ Math.ceil(section.entries.length / PAGE_SIZE) }}
            <span class="ml-1 grey--text text--darken-1">({{ section.entries.length }} total)</span>
          </span>
          <v-btn
            icon
            x-small
            :disabled="section.page >= Math.ceil(section.entries.length / PAGE_SIZE)"
            @click="section.page += 1"
          >
            <v-icon size="18">mdi-chevron-right</v-icon>
          </v-btn>
        </div>
      </div>

    </v-card>

  </v-container>
</template>

<script>
import AttributesTable from '@/components/Devices/AttributesTable.vue';
import { getResolvedSessionsRegistrations } from '@/database/queries/resolved_sessions_registrations.js';
import { getDB } from '@/database/index.js';

// ponytail: getUnlinkedClusters unused while right column is hidden
// import { getUnlinkedClusters } from '@/database/queries/instances_v2.js';

export default {
  name: 'DevicesMockup',
  components: { AttributesTable },
  data() {
    return {
      platforms: [],
      PAGE_SIZE: 5
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
    goToEventsPage(query) {
      if (this.$router && query) {
        var routeName = this.$route.name === 'DemoDevices' ? 'DemoEvents' : 'Events';
        this.$router.push({ name: routeName, query: { q: query } }).catch(function() {});
      }
    },
    async fetchLiveData() {
      try {
        var db = await getDB();

        var uploads = await db.exec('SELECT * FROM uploads', {
          returnValue: 'resultRows',
          rowMode: 'object'
        });

        var states = await getResolvedSessionsRegistrations();

        var platformMeta = {
          facebook: { displayName: 'Facebook', icon: 'mdi-facebook', color: '#5E75C2' },
          google:   { displayName: 'Google',   icon: 'mdi-google',   color: '#FD7EAC' },
          apple:    { displayName: 'Apple/iCloud', icon: 'mdi-apple', color: '#000000' },
          discord:  { displayName: 'Discord',  icon: 'mdi-discord',  color: '#5865F2' },
          instagram:{ displayName: 'Instagram',icon: 'mdi-instagram',color: '#E1306C' }
        };

        var entityIcons = {
          session:                  'mdi-cookie-outline',
          app_registration:         'mdi-cellphone-link',
          hardware_registration:    'mdi-cellphone',
          platform_inferred_device: 'mdi-account-clock-outline'
        };

        // Section definitions: order, label, description, detailLabel
        var sectionDefs = [
          {
            key: 'session',
            label: 'Session History',
            description: 'Cookie-bound login states. Temporary, tied to current authentication cookies.',
            detailLabel: 'Session Attributes',
            sortByLastSeen: true
          },
          {
            key: 'app_registration',
            label: 'App Registrations',
            description: 'Installed client applications (usually with push tokens). Persistent client installs on devices.',
            detailLabel: 'App Registration Details',
            sortByLastSeen: false
          },
          {
            key: 'hardware_registration',
            label: 'Hardware Registrations',
            description: 'Verified physical hardware profiles (linked to Apple ID or Google devices). Cryptographically or OS-verified.',
            detailLabel: 'Hardware Registry Details',
            sortByLastSeen: false
          },
          {
            key: 'platform_inferred_device',
            label: 'Platform-Inferred Devices',
            description: 'Devices inferred by the platform from activity patterns, not explicitly registered.',
            detailLabel: 'Device Attributes',
            sortByLastSeen: false
          }
        ];

        var TIMESTAMP_KEYS = ['entity_first_seen_timestamp', 'entity_last_seen_timestamp', 'timestamp'];

        this.platforms = uploads.map(function(upload) {
          var platformKey = (upload.platform || '').toLowerCase();
          var meta = platformMeta[platformKey] || { displayName: upload.platform, icon: 'mdi-account', color: '#757575' };

          var uploadEntries = states
            .filter(function(s) { return s.upload_id === upload.id; })
            .map(function(s) {
              var firstSeen = s.attributes.entity_first_seen_timestamp || null;
              var lastSeen  = s.attributes.entity_last_seen_timestamp || null;
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
                title: s.model_name,
                client_name: s.client_name,
                icon: entityIcons[s.entity_type] || 'mdi-devices',
                firstSeen: firstSeen,
                lastSeen: lastSeen,
                location: location,
                is_reduced_ua: s.is_reduced_ua,
                user_agent_original: s.user_agent_original || null,
                has_trusted_cookie: s.has_trusted_cookie,
                has_passkey: s.has_passkey,
                registration_device: s.registration_device,
                event_count: s.event_count,
                events_query: s.events_query,
                formatted_attributes: formattedAttrs
              };
            });

          var sections = sectionDefs.map(function(def) {
            var entries = uploadEntries.filter(function(e) { return e.entity_type === def.key; });
            if (def.sortByLastSeen) {
              entries = entries.slice().sort(function(a, b) {
                if (!a.lastSeen && !b.lastSeen) return 0;
                if (!a.lastSeen) return 1;
                if (!b.lastSeen) return -1;
                return a.lastSeen < b.lastSeen ? 1 : a.lastSeen > b.lastSeen ? -1 : 0;
              });
            }
            return {
              key: def.key,
              label: def.label,
              description: def.description,
              detailLabel: def.detailLabel,
              entries: entries,
              page: 1
            };
          });

          return {
            displayName: meta.displayName,
            accountLabel: upload.given_name || 'Primary Account',
            icon: meta.icon,
            color: meta.color,
            sections: sections
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
.min-h-100 {
  min-height: 100vh;
}
.border {
  border: 1px solid #e0e0e0;
}
.border-top {
  border-top: 1px solid #e0e0e0;
}
.w-100 {
  width: 100%;
}
.shadow-sm {
  box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.1);
}
</style>
