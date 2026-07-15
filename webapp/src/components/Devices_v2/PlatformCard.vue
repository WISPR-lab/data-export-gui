// added for WISPR-lab/data-export-gui
<template>
  <v-card outlined class="rounded-xl mb-6 shadow-sm overflow-hidden" style="background-color: white;">

    <!-- Header / collapse toggle -->
    <div
      class="d-flex align-center justify-space-between pa-5 pb-3 cursor-pointer"
      @click="collapsed = !collapsed"
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
        <h2 class="text-subtitle-1 font-weight-bold text--primary mb-0 text-truncate min-width-0">
          {{ platform.accountLabel }}
        </h2>
      </div>
      <v-btn icon>
        <v-icon>{{ collapsed ? 'mdi-chevron-down' : 'mdi-chevron-up' }}</v-icon>
      </v-btn>
    </div>

    <!-- Collapsible card content -->
    <v-slide-y-transition>
      <div v-show="!collapsed">
        
        <!-- Tabs -->
        <v-tabs
          v-model="activeTab"
          class="px-5 mt-1"
          color="primary"
          background-color="transparent"
          grow
        >
          <v-tab class="text-body-2 font-weight-medium text-capitalize">
            {{ tab1Label }}
            <v-chip x-small class="ml-2" color="grey lighten-3" style="height: 18px;">
              {{ platform.totalGroundTruth }}
            </v-chip>
          </v-tab>
          <v-tab class="text-body-2 font-weight-medium text-capitalize">
            {{ tab2Label }}
            <v-chip x-small class="ml-2" color="grey lighten-3" style="height: 18px;">
              {{ platform.clusters.length }}
            </v-chip>
          </v-tab>
        </v-tabs>

        <v-divider></v-divider>

        <v-tabs-items v-model="activeTab" class="pa-5">

          <!-- TAB 1: Platform Exported Records -->
          <v-tab-item>
            <div
              v-for="section in activeSections"
              :key="section.key"
              class="mb-8"
            >
              <!-- Section Header -->
              <div class="d-flex align-center mb-3">
                <h3 class="text-body-1 font-weight-bold text--primary mb-0 mr-2">{{ section.label }}</h3>
                <v-btn
                  v-if="section.description"
                  icon x-small color="blue darken-2"
                  @click.stop="openInfoModal(section.label, section.description)"
                >
                  <v-icon size="16">mdi-information-outline</v-icon>
                </v-btn>
              </div>

              <!-- Platform-inferred badge -->
              <div
                v-if="section.key === 'platform_inferred_device'"
                class="platform-badge d-flex align-center pa-2 rounded-lg mb-3"
                style="gap: 6px;"
              >
                <v-icon size="14" color="blue darken-2">mdi-check-decagram</v-icon>
                <span class="text-body-2 blue--text text--darken-2">{{ platformBadgeText }}</span>
              </div>

              <!-- Expansion Panels for Records -->
              <v-expansion-panels flat class="device-panels">
                <device-row
                  v-for="(entry, eIdx) in pageSlice(section)"
                  :key="section.key + '-' + eIdx"
                  type="record"
                  :title="entry.title"
                  :client-name="entry.client_name"
                  :icon="entry.icon"
                  :first-seen="entry.firstSeen"
                  :last-seen="entry.lastSeen"
                  :events-query="entry.events_query"
                  :is-reduced-ua="entry.is_reduced_ua"
                  :has-passkey="entry.has_passkey"
                  :detail-label="section.detailLabel"
                  :formatted-attributes="entry.formatted_attributes"
                  :event-count="entry.event_count"
                  @show-info="openInfoModal($event.title, $event.description)"
                />
              </v-expansion-panels>

              <!-- Section pagination -->
              <div v-if="section.entries.length > pageSize" class="d-flex align-center justify-center mt-2" style="gap: 6px;">
                <v-btn icon x-small :disabled="section.page <= 1" @click="section.page -= 1">
                  <v-icon size="16">mdi-chevron-left</v-icon>
                </v-btn>
                <span class="text-body-2 text--secondary">
                  {{ section.page }} / {{ Math.ceil(section.entries.length / pageSize) }}
                  <span class="grey--text text--darken-1 ml-1">({{ section.entries.length }} total)</span>
                </span>
                <v-btn icon x-small :disabled="section.page >= Math.ceil(section.entries.length / pageSize)" @click="section.page += 1">
                  <v-icon size="16">mdi-chevron-right</v-icon>
                </v-btn>
              </div>
            </div>

            <div
              v-if="!activeSections.length"
              class="text-body-2 text--secondary italic pa-6 text-center grey lighten-5 rounded-xl"
            >
              No platform records found for this account.
            </div>
          </v-tab-item>

          <!-- TAB 2: Inferred Activity Clusters -->
          <v-tab-item>
            <div class="mb-4">
              <p class="text-body-2 text--secondary mb-0" style="line-height: 1.6;">
                LEStrADE's analysis of different possible device fingerprints corresponding to different events (e.g., logins, password changes).
                This is a <strong>conservative</strong> estimate: multiple clusters may actually belong to the same device,
                especially on iOS where Apple's privacy features make devices harder to distinguish.
              </p>
            </div>

            <div
              v-if="!platform.clusters.length"
              class="text-body-2 text--secondary italic pa-6 text-center grey lighten-5 rounded-xl"
            >
              No activity clusters detected for this account.
            </div>

            <div v-else>
              <!-- Cluster Rows using DeviceRow wrapped in expansion panels to match structure/styling -->
              <v-expansion-panels flat class="device-panels">
                <device-row
                  v-for="(cluster, cIdx) in currentClusterPage"
                  :key="'cluster-' + cIdx"
                  type="activity"
                  :title="cluster.title"
                  :client-name="cluster.norm_client"
                  :icon="clusterIcon(cluster)"
                  :first-seen="cluster.first_seen"
                  :last-seen="cluster.last_seen"
                  :fallback-date-str="cluster.dateString"
                  :events-query="cluster.query"
                  :event-count="cluster.event_count"
                  :cluster-raw="cluster"
                />
              </v-expansion-panels>

              <!-- Cluster pagination -->
              <div v-if="platform.clusters.length > pageSize" class="d-flex align-center justify-center mt-2" style="gap: 6px;">
                <v-btn icon x-small :disabled="platform.clusterPage <= 1" @click="$emit('update:clusterPage', platform.clusterPage - 1)">
                  <v-icon size="16">mdi-chevron-left</v-icon>
                </v-btn>
                <span class="text-body-2 text--secondary">
                  {{ platform.clusterPage }} / {{ Math.ceil(platform.clusters.length / pageSize) }}
                  <span class="grey--text text--darken-1 ml-1">({{ platform.clusters.length }} total)</span>
                </span>
                <v-btn icon x-small :disabled="platform.clusterPage >= Math.ceil(platform.clusters.length / pageSize)" @click="$emit('update:clusterPage', platform.clusterPage + 1)">
                  <v-icon size="16">mdi-chevron-right</v-icon>
                </v-btn>
              </div>
            </div>
          </v-tab-item>

        </v-tabs-items>
      </div>
    </v-slide-y-transition>

    <!-- Info Modal -->
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
  </v-card>
</template>

<script>
import DeviceRow from './DeviceRow.vue';

export default {
  name: 'PlatformCard',
  components: { DeviceRow },
  props: {
    platform: { type: Object, required: true },
    pageSize: { type: Number, required: true }
  },
  data() {
    return {
      collapsed: false,
      activeTab: 0,
      infoModal: { open: false, title: '', description: '' }
    };
  },
  computed: {
    tab1Label() {
      return 'Devices & Sessions reported by ' + this.platform.displayName;
    },
    tab2Label() {
      return 'Additional Activity Clusters Inferred by LEStrADE';
    },
    platformBadgeText() {
      return 'Reported directly by ' + this.platform.displayName + ' — this is the platform\'s own device recognition.';
    },
    activeSections() {
      return this.platform.sections.filter(function(s) { return s.entries.length > 0; });
    },
    currentClusterPage() {
      var start = (this.platform.clusterPage - 1) * this.pageSize;
      return this.platform.clusters.slice(start, start + this.pageSize);
    }
  },
  methods: {
    pageSlice(section) {
      var start = (section.page - 1) * this.pageSize;
      return section.entries.slice(start, start + this.pageSize);
    },
    clusterIcon(cluster) {
      var os = (cluster.os_type || '').toLowerCase();
      if (os.indexOf('ios') !== -1 || os.indexOf('iphone') !== -1) return 'mdi-apple-ios';
      if (os.indexOf('mac') !== -1)     return 'mdi-laptop-mac';
      if (os.indexOf('android') !== -1) return 'mdi-android';
      if (os.indexOf('windows') !== -1) return 'mdi-microsoft-windows';
      return 'mdi-monitor-cellphone';
    },
    formatActiveRange(firstSeen, lastSeen, fallbackStr) {
      if (!firstSeen && !lastSeen) return fallbackStr || '';
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
        var range = fmt([normalize(firstSeen), normalize(lastSeen)]);
        return range ? 'Active ' + range : (fallbackStr || '');
      }
      return fallbackStr || '';
    },
    openInfoModal(title, description) {
      this.infoModal.title = title;
      this.infoModal.description = description;
      this.infoModal.open = true;
    }
  }
};
</script>

<style scoped>
.shadow-sm { box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.1); }
.cursor-pointer { cursor: pointer; }
.platform-badge {
  background-color: #e3f2fd;
  border: 1px solid #90caf9;
}
</style>
