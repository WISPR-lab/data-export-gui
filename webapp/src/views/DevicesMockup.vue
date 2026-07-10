// added for WISPR-lab/data-export-gui
<template>
  <v-container class="pa-6 white min-h-100" style="max-width: 1200px;">

    <!-- Page Header -->
    <div class="mb-6">
      <h1 class="text-h4 text--primary mb-1">Devices (Mockup)</h1>
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
          <h2 class="text-subtitle-1 text--primary font-weight-medium mb-0">{{ platform.displayName }} Account</h2>
          <div class="text-caption text--secondary">{{ platform.accountLabel }}</div>
        </div>
      </div>

      <!-- Two-Column Grid Within Each Platform -->
      <v-row>
        
        <!-- COLUMN 1: Sessions & Registrations (Left side) -->
        <v-col cols="12" md="6" class="pr-md-4">
          
          <!-- Sub-section 1: Active Sessions -->
          <div class="mb-6">
            <h3 class="text-subtitle-2 font-weight-bold grey--text text--darken-2 mb-1">Active Sessions</h3>
            <p class="text-caption text--secondary mb-3">
              Cookie-bound login states. Temporary, tied to current authentication cookies.
            </p>
            
            <div v-if="!platform.sessions.length" class="text-caption text--secondary italic pa-2 border rounded-xl text-center grey lighten-5 mb-4">
              No active session cookies found.
            </div>
            
            <v-expansion-panels flat class="device-panels">
              <v-expansion-panel
                v-for="(entry, eIdx) in platform.sessions"
                :key="'sess-' + eIdx"
                class="mb-3 border rounded-xl overflow-hidden device-profile-card"
              >
                <v-expansion-panel-header class="pa-4">
                  <template v-slot:default="{ open }">
                    <div class="device-header-row py-1 d-flex align-center justify-space-between w-100">
                      <div class="d-flex align-center flex-grow-1 min-width-0">
                        <v-avatar size="40" color="grey lighten-5" class="mr-4 flex-shrink-0">
                          <v-icon color="grey darken-3" size="20">{{ entry.icon }}</v-icon>
                        </v-avatar>
                        
                        <div class="d-flex flex-column min-width-0">
                          <div class="d-flex flex-wrap align-baseline">
                            <span class="text-subtitle-2 text--primary font-weight-medium text-truncate">
                              {{ entry.title }}
                            </span>
                            <span v-if="entry.client_name" class="text-caption text--secondary font-weight-regular ml-2">
                              via {{ entry.client_name }}
                            </span>
                          </div>
                          <div class="text-caption text--secondary mt-0.5 text-truncate">
                            <span>{{ entry.dateString || 'Active Session' }}</span>
                            <span v-if="entry.location"> • {{ entry.location }}</span>
                          </div>
                        </div>
                      </div>
                      
                      <!-- Right Side Chips & Button -->
                      <div class="text-right mr-4 flex-shrink-0 d-flex align-center justify-end" style="gap: 8px;">
                        <v-tooltip v-if="entry.is_reduced_ua" bottom max-width="320">
                          <template v-slot:activator="{ on, attrs }">
                            <v-chip
                              small
                              color="grey lighten-2"
                              class="font-weight-medium flex-shrink-0 grey--text text--darken-3 px-2"
                              style="height: 22px; font-size: 11px;"
                              v-bind="attrs"
                              v-on="on"
                            >
                              <v-icon left small class="grey--text text--darken-3" style="font-size: 12px; margin-right: 4px;">mdi-fingerprint-off</v-icon>
                              Reduced UA
                            </v-chip>
                          </template>
                          <span>To prevent fingerprinting, browsers on iPhones use generic User-Agents that hide the exact model.</span>
                        </v-tooltip>

                        <v-chip v-if="entry.has_trusted_cookie" small color="primary" outlined class="px-2" style="height: 22px; font-size: 11px;">
                          Cookie
                        </v-chip>

                        <v-btn
                          v-if="entry.event_count"
                          text
                          small
                          color="primary"
                          class="text-capitalize px-1 min-width-0"
                          style="height: 28px; font-size: 12px;"
                          @click.stop="goToEventsPage(entry.events_query)"
                        >
                          {{ entry.event_count }} Events
                          <v-icon right small style="margin-left: 2px; font-size: 14px;">mdi-arrow-right</v-icon>
                        </v-btn>
                      </div>
                    </div>
                  </template>
                </v-expansion-panel-header>
                <v-expansion-panel-content class="grey lighten-5 border-top">
                  <div class="pa-4">
                    <div class="text-caption text--primary font-weight-medium mb-2">Session Attributes</div>
                    <attributes-table :attributes="entry.formatted_attributes" />
                  </div>
                </v-expansion-panel-content>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>

          <!-- Sub-section 2: App Registrations -->
          <div class="mb-6">
            <h3 class="text-subtitle-2 font-weight-bold grey--text text--darken-2 mb-1">App Registrations</h3>
            <p class="text-caption text--secondary mb-3">
              Installed client applications (usually with push tokens). Persistent client installs on devices.
            </p>
            
            <div v-if="!platform.appRegistrations.length" class="text-caption text--secondary italic pa-2 border rounded-xl text-center grey lighten-5 mb-4">
              No registered client apps.
            </div>

            <v-expansion-panels flat class="device-panels">
              <v-expansion-panel
                v-for="(entry, eIdx) in platform.appRegistrations"
                :key="'app-' + eIdx"
                class="mb-3 border rounded-xl overflow-hidden device-profile-card"
              >
                <v-expansion-panel-header class="pa-4">
                  <template v-slot:default="{ open }">
                    <div class="device-header-row py-1 d-flex align-center justify-space-between w-100">
                      <div class="d-flex align-center flex-grow-1 min-width-0">
                        <v-avatar size="40" color="grey lighten-5" class="mr-4 flex-shrink-0">
                          <v-icon color="grey darken-3" size="20">{{ entry.icon }}</v-icon>
                        </v-avatar>
                        
                        <div class="d-flex flex-column min-width-0">
                          <div class="d-flex flex-wrap align-baseline">
                            <span class="text-subtitle-2 text--primary font-weight-medium text-truncate">
                              {{ entry.title }}
                            </span>
                            <span v-if="entry.client_name" class="text-caption text--secondary font-weight-regular ml-2">
                              via {{ entry.client_name }}
                            </span>
                          </div>
                          <div class="text-caption text--secondary mt-0.5 text-truncate">
                            <span>{{ entry.dateString || 'App Registration' }}</span>
                            <span v-if="entry.location"> • {{ entry.location }}</span>
                          </div>
                        </div>
                      </div>
                      
                      <!-- Right Side Chips & Button -->
                      <div class="text-right mr-4 flex-shrink-0 d-flex align-center justify-end" style="gap: 8px;">
                        <v-btn
                          v-if="entry.event_count"
                          text
                          small
                          color="primary"
                          class="text-capitalize px-1 min-width-0"
                          style="height: 28px; font-size: 12px;"
                          @click.stop="goToEventsPage(entry.events_query)"
                        >
                          {{ entry.event_count }} Events
                          <v-icon right small style="margin-left: 2px; font-size: 14px;">mdi-arrow-right</v-icon>
                        </v-btn>
                      </div>
                    </div>
                  </template>
                </v-expansion-panel-header>
                <v-expansion-panel-content class="grey lighten-5 border-top">
                  <div class="pa-4">
                    <div class="text-caption text--primary font-weight-medium mb-2">App Registration Details</div>
                    <attributes-table :attributes="entry.formatted_attributes" />
                  </div>
                </v-expansion-panel-content>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>

          <!-- Sub-section 3: Hardware Registrations -->
          <div v-if="platform.hardwareRegistrations.length">
            <h3 class="text-subtitle-2 font-weight-bold grey--text text--darken-2 mb-1">Hardware Registrations</h3>
            <p class="text-caption text--secondary mb-3">
              Verified physical hardware profiles (linked to Apple ID or Google devices). Cryptographically or OS-verified.
            </p>

            <v-expansion-panels flat class="device-panels">
              <v-expansion-panel
                v-for="(entry, eIdx) in platform.hardwareRegistrations"
                :key="'hw-' + eIdx"
                class="mb-3 border rounded-xl overflow-hidden device-profile-card"
              >
                <v-expansion-panel-header class="pa-4">
                  <template v-slot:default="{ open }">
                    <div class="device-header-row py-1 d-flex align-center justify-space-between w-100">
                      <div class="d-flex align-center flex-grow-1 min-width-0">
                        <v-avatar size="40" color="grey lighten-5" class="mr-4 flex-shrink-0">
                          <v-icon color="grey darken-3" size="20">{{ entry.icon }}</v-icon>
                        </v-avatar>
                        
                        <div class="d-flex flex-column min-width-0">
                          <div class="d-flex flex-wrap align-baseline">
                            <span class="text-subtitle-2 text--primary font-weight-medium text-truncate">
                              {{ entry.title }}
                            </span>
                            <span v-if="entry.client_name" class="text-caption text--secondary font-weight-regular ml-2">
                              via {{ entry.client_name }}
                            </span>
                          </div>
                          <div class="text-caption text--secondary mt-0.5 text-truncate">
                            <span>{{ entry.dateString || 'Hardware Registration' }}</span>
                            <span v-if="entry.location"> • {{ entry.location }}</span>
                          </div>
                        </div>
                      </div>
                      
                      <!-- Right Side Chips & Button -->
                      <div class="text-right mr-4 flex-shrink-0 d-flex align-center justify-end" style="gap: 8px;">
                        <v-chip v-if="entry.has_passkey" small color="success" outlined class="px-2" style="height: 22px; font-size: 11px;">
                          Passkey
                        </v-chip>

                        <v-btn
                          v-if="entry.event_count"
                          text
                          small
                          color="primary"
                          class="text-capitalize px-1 min-width-0"
                          style="height: 28px; font-size: 12px;"
                          @click.stop="goToEventsPage(entry.events_query)"
                        >
                          {{ entry.event_count }} Events
                          <v-icon right small style="margin-left: 2px; font-size: 14px;">mdi-arrow-right</v-icon>
                        </v-btn>
                      </div>
                    </div>
                  </template>
                </v-expansion-panel-header>
                <v-expansion-panel-content class="grey lighten-5 border-top">
                  <div class="pa-4">
                    <div class="text-caption text--primary font-weight-medium mb-2">Hardware Registry Details</div>
                    <attributes-table :attributes="entry.formatted_attributes" />
                  </div>
                </v-expansion-panel-content>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>

        </v-col>

        <!-- COLUMN 2: Unlinked Activity (Right side) -->
        <v-col cols="12" md="6" class="pl-md-4 border-left">
          <h3 class="text-subtitle-2 font-weight-bold grey--text text--darken-2 mb-1">Unlinked Activity</h3>
          <p class="text-caption text--secondary mb-4">
            Logins/activity with no active session cookie. Query events grouped under this instance.
          </p>
          
          <div v-if="!platform.unlinkedClusters.length" class="text-caption text--secondary italic pa-4 border rounded-xl text-center grey lighten-5">
            No unlinked activity clusters.
          </div>

          <div v-else class="d-flex flex-column" style="gap: 12px;">
            <div
              v-for="(cluster, cIdx) in platform.unlinkedClusters"
              :key="'cluster-' + cIdx"
              class="unlinked-activity-row pa-3 d-flex align-center justify-space-between"
            >
              <div class="min-width-0 mr-2">
                <div class="text-caption font-weight-bold text--primary text-truncate">
                  {{ cluster.title }}
                </div>
                <div class="text-caption text--secondary mt-0.5 text-truncate">
                  Active {{ cluster.dateString }}
                </div>
              </div>

              <!-- Query directly by instance identifier -->
              <v-btn
                v-if="cluster.event_count"
                small
                text
                color="primary"
                class="text-capitalize px-2 font-weight-medium flex-shrink-0"
                @click.stop="goToEventsPage(cluster.query)"
              >
                View {{ cluster.event_count }} Events
                <v-icon right size="14" class="ml-1">mdi-arrow-right</v-icon>
              </v-btn>
            </div>
          </div>
        </v-col>

      </v-row>
    </v-card>

  </v-container>
</template>

<script>
import AttributesTable from '@/components/Devices/AttributesTable.vue';
import { getResolvedSessionsRegistrations } from '@/database/queries/resolved_sessions_registrations.js';
import { getUnlinkedClusters } from '@/database/queries/instances_v2.js';
import { getDB } from '@/database/index.js';

export default {
  name: 'DevicesMockup',
  components: {
    AttributesTable
  },
  data() {
    return {
      platforms: []
    }
  },
  mounted() {
    this.fetchLiveData();
  },
  methods: {
    goToEventsPage(query) {
      if (this.$router && query) {
        const routeName = this.$route.name === 'DemoDevices' ? 'DemoEvents' : 'Events';
        this.$router.push({
          name: routeName,
          query: { q: query }
        }).catch(err => {});
      }
    },
    async fetchLiveData() {
      try {
        const db = await getDB();
        
        // Fetch platform uploads/accounts
        const uploads = await db.exec("SELECT * FROM uploads", {
          returnValue: 'resultRows',
          rowMode: 'object'
        });

        const states = await getResolvedSessionsRegistrations();
        const clusters = await getUnlinkedClusters();

        const platformMeta = {
          facebook: { displayName: 'Facebook', icon: 'mdi-facebook', color: '#5E75C2' },
          google: { displayName: 'Google', icon: 'mdi-google', color: '#FD7EAC' },
          apple: { displayName: 'Apple/iCloud', icon: 'mdi-apple', color: '#000000' },
          discord: { displayName: 'Discord', icon: 'mdi-discord', color: '#5865F2' },
          instagram: { displayName: 'Instagram', icon: 'mdi-instagram', color: '#E1306C' }
        };

        const entityIcons = {
          session: 'mdi-cookie-outline',
          app_registration: 'mdi-cellphone-link',
          hardware_registration: 'mdi-cellphone',
          platform_inferred_device: 'mdi-account-clock-outline'
        };

        const formatDate = (dateStr) => {
          if (!dateStr) return null;
          try {
            const date = new Date(dateStr);
            if (isNaN(date.getTime())) return null;
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
          } catch (e) {
            return null;
          }
        };

        this.platforms = uploads.map(upload => {
          const platformKey = (upload.platform || '').toLowerCase();
          const meta = platformMeta[platformKey] || { displayName: upload.platform, icon: 'mdi-account', color: '#757575' };

          // Filter states belonging to this upload
          const uploadEntries = states
            .filter(s => s.upload_id === upload.id)
            .map(s => {
              const firstSeen = s.attributes.created_timestamp || s.attributes.first_seen_time || s.attributes.device_added_date;
              const lastSeen = s.attributes.updated_timestamp || s.attributes.last_seen_time || s.attributes.device_last_heartbeat_timestamp;
              
              let dateString = '';
              const firstStr = formatDate(firstSeen);
              const lastStr = formatDate(lastSeen);
              if (firstStr && lastStr && firstStr !== lastStr) {
                dateString = `Active ${firstStr} – ${lastStr}`;
              } else if (lastStr) {
                dateString = `Last Active: ${lastStr}`;
              } else if (firstStr) {
                dateString = `Active: ${firstStr}`;
              }

              const location = s.attributes.location || s.attributes.device_last_location || '';

              const formattedAttrs = Object.entries(s.attributes)
                .filter(([k, v]) => !k.startsWith('norm__') && v !== null && v !== '')
                .map(([k, v]) => {
                  let valStr = String(v);
                  if (typeof v === 'object') {
                    valStr = JSON.stringify(v, null, 2);
                  }
                  const label = k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                  return { label, value: valStr };
                });

              return {
                id: s.id,
                entity_type: s.entity_type,
                title: s.model_name,
                client_name: s.client_name,
                icon: entityIcons[s.entity_type] || 'mdi-devices',
                dateString,
                location,
                is_reduced_ua: s.is_reduced_ua,
                has_trusted_cookie: s.has_trusted_cookie,
                has_passkey: s.has_passkey,
                registration_device: s.registration_device,
                event_count: s.event_count,
                events_query: s.events_query,
                formatted_attributes: formattedAttrs
              };
            });

          // Separate into distinct sections
          const sessions = uploadEntries.filter(e => e.entity_type === 'session');
          const appRegistrations = uploadEntries.filter(e => e.entity_type === 'app_registration');
          const hardwareRegistrations = uploadEntries.filter(e => e.entity_type === 'hardware_registration');

          // Filter clusters belonging to this upload and query by instance ID
          const uploadClusters = clusters
            .filter(c => c.upload_id === upload.id)
            .map(c => {
              const title = c.norm_client ? `${c.norm_client} (${c.title})` : c.title;
              return {
                ...c,
                title,
                query: c.query
              };
            });

          return {
            displayName: meta.displayName,
            accountLabel: upload.given_name || 'Primary Account',
            icon: meta.icon,
            color: meta.color,
            sessions,
            appRegistrations,
            hardwareRegistrations,
            unlinkedClusters: uploadClusters
          };
        });

      } catch (err) {
        console.error('Error fetching live DB data for mockup:', err);
      }
    }
  }
}
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
.border-left {
  border-left: 1px solid #e0e0e0;
}
.w-100 {
  width: 100%;
}
.shadow-sm {
  box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.1);
}
.unlinked-activity-row {
  background-color: #fafafa;
  border: 1px dashed #bdbdbd !important;
  border-radius: 8px;
}
.italic {
  font-style: italic;
}
</style>
