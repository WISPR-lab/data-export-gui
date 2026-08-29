// added for anonymous-research-group/data-export-gui
<template>
  <v-card outlined class="rounded-lg mb-6 overflow-hidden" style="background-color: white;">

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
              {{ platform.groups.length }}
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
              <div class="mb-2">
                <h3 class="text-body-1 font-weight-bold text--primary mb-1">{{ section.label }}</h3>
                <p class="text-body-2 text--secondary mb-0" style="line-height: 1.6;">{{ section.description }}</p>
              </div>

              <!-- Top Footer below text, right-aligned -->
              <div v-if="section.entries.length > 0" class="d-flex justify-end mb-2">
                <v-data-footer
                  :pagination="sectionPagination(section)"
                  :options="sectionOptions(section)"
                  @update:options="onUpdateSectionOptions(section, $event)"
                  :show-current-page="true"
                  :items-per-page-options="[10, 20, 50, 100]"
                  items-per-page-text="Rows per page:"
                  style="border: 0"
                  class="mr-n3"
                ></v-data-footer>
              </div>

              <!-- Platform-inferred badge -->
              <!-- <div
                v-if="section.key === 'platform_inferred_device'"
                class="platform-badge d-flex align-center pa-2 rounded-lg mb-3"
                style="gap: 6px;"
              >
                <v-icon size="14" color="blue darken-2">mdi-check-decagram</v-icon>
                <span class="text-body-2 blue--text text--darken-2">{{ platformBadgeText }}</span>
              </div> -->

              <!-- Expansion Panels for Records -->
              <v-expansion-panels multiple flat class="device-panels">
                <device-row
                  v-for="(entry, eIdx) in pageSlice(section)"
                  :key="section.key + '-' + (entry.id || eIdx)"
                  type="record"
                  :id="entry.id"
                  :tags="entry.tags"
                  :title="entry.title"
                  :client-name="entry.client_name"
                  :icon="entry.icon"
                  :first-seen="entry.firstSeen"
                  :last-seen="entry.lastSeen"
                  :events-query="entry.events_query"
                  :is-reduced-ua="entry.is_reduced_ua == 1"
                  :is-inactive="entry.is_inactive"
                  :entity-sub-type="section.key"
                  :has-passkey="entry.has_passkey"
                  :detail-label="section.detailLabel"
                  :formatted-attributes="entry.formatted_attributes"
                  :event-count="entry.event_count"
                  @show-info="openInfoModal($event.title, $event.description)"
                />
              </v-expansion-panels>
            </div>

            <div
              v-if="!activeSections.length"
              class="text-body-2 text--secondary italic pa-6 text-center grey lighten-5 rounded-lg"
            >
              This platform has not explicitly provided a file containing a list of logged-in devices or active sessions associated with this account. 
              In the "Events Groups..." tab, you can see our best-effort grouping of different login (and other) events by their origin. 
            </div>
          </v-tab-item>

          <!-- TAB 2: groups -->
          <v-tab-item>
            <div class="mb-2">
              <p class="text-body-2 text--secondary mb-0" style="line-height: 1.6;">
                LEStrADE's analysis of different possible device fingerprints corresponding to different events (e.g., logins, password changes). 
                Each of the following is an "event group" that may correspond to a single device. 
                Not every event in the database may be linked to one of the below event groups as some events are recorded without any device information. 
                This is a <strong>conservative</strong> estimate: multiple event groups may actually originate from the same device, especially on iOS where Apple's privacy features make devices harder to distinguish.
              </p>
            </div>

            <!-- Top Footer below description text, right-aligned -->
            <div v-if="platform.groups.length > 0" class="d-flex justify-end mb-2">
              <v-data-footer
                :pagination="groupPagination()"
                :options="groupOptions()"
                @update:options="onUpdateGroupOptions($event)"
                :show-current-page="true"
                :items-per-page-options="[10, 20, 50, 100]"
                items-per-page-text="Rows per page:"
                style="border: 0"
                class="mr-n3"
              ></v-data-footer>
            </div>

            <div
              v-if="!platform.groups.length"
              class="text-body-2 text--secondary italic pa-6 text-center grey lighten-5 rounded-lg"
            >
              No event groups detected for this account.
            </div>

            <div v-else>
              <!-- Group Rows using DeviceRow wrapped in expansion panels to match structure/styling -->
              <v-expansion-panels multiple flat class="device-panels">
                <device-row
                  v-for="(group, groupIdx) in currentGroupPage"
                  :key="'group-' + (group.id || groupIdx)"
                  type="activity"
                  :id="group.id"
                  :tags="group.tags"
                  :title="group.title"
                  :client-name="group.norm_client"
                  :icon="groupIcon(group)"
                  :first-seen="group.first_seen"
                  :last-seen="group.last_seen"
                  :fallback-date-str="group.dateString"
                  :events-query="group.query"
                  :event-count="group.event_count"
                  :is-reduced-ua="group.apple_masking == 1"
                  :has-conflicting-hardware-ids="group.has_conflicting_hardware_ids == 1"
                  :group-raw="group"
                  @show-info="openInfoModal($event.title, $event.description)"
                />
              </v-expansion-panels>
            </div>
          </v-tab-item>

        </v-tabs-items>
      </div>
    </v-slide-y-transition>

    <!-- Info Modal -->
    <v-dialog v-model="infoModal.open" max-width="450">
      <v-card class="rounded-lg">
        <v-card-title class="d-flex justify-space-between align-center text-h6 font-weight-bold pt-4 pb-2 px-6">
          <span>{{ infoModal.title }}</span>
          <v-btn icon small @click="infoModal.open = false" title="Close dialog">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text class="text-body-2 text--secondary px-6 pb-6 pt-2" style="line-height: 1.6;">
          {{ infoModal.description }}
        </v-card-text>
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
      infoModal: { open: false, title: '', description: '' },
      sectionPages: {},
      sectionSizes: {},
      groupPage: 1,
      groupSize: 10
    };
  },
  computed: {
    tab1Label() {
      return 'Devices & Sessions reported by ' + this.platform.displayName;
    },
    tab2Label() {
      return 'Event groups that may be linked to devices';
    },
    activeSections() {
      return this.platform.sections.filter(function(s) { return s.entries.length > 0; });
    },
    currentGroupPage() {
      var page = this.groupPage || 1;
      var perPage = this.groupSize || this.pageSize;
      var start = (page - 1) * perPage;
      return this.platform.groups.slice(start, start + perPage);
    }
  },
  methods: {
    getSectionPage(section) {
      return this.sectionPages[section.key] || 1;
    },
    getSectionSize(section) {
      return this.sectionSizes[section.key] || this.pageSize;
    },
    pageSlice(section) {
      var page = this.getSectionPage(section);
      var perPage = this.getSectionSize(section);
      var start = (page - 1) * perPage;
      return section.entries.slice(start, start + perPage);
    },
    sectionPagination(section) {
      var total = section.entries.length;
      var page = this.getSectionPage(section);
      var perPage = this.getSectionSize(section);
      return {
        page: page,
        itemsPerPage: perPage,
        pageStart: total === 0 ? 0 : (page - 1) * perPage,
        pageStop: Math.min(page * perPage, total),
        pageCount: Math.ceil(total / perPage),
        itemsLength: total
      };
    },
    sectionOptions(section) {
      return {
        page: this.getSectionPage(section),
        itemsPerPage: this.getSectionSize(section)
      };
    },
    onUpdateSectionOptions(section, opts) {
      if (opts.page) {
        this.$set(this.sectionPages, section.key, opts.page);
      }
      if (opts.itemsPerPage && opts.itemsPerPage !== this.getSectionSize(section)) {
        this.$set(this.sectionSizes, section.key, opts.itemsPerPage);
        this.$set(this.sectionPages, section.key, 1);
      }
    },
    groupPagination() {
      var total = this.platform.groups.length;
      var page = this.groupPage || 1;
      var perPage = this.groupSize || this.pageSize;
      return {
        page: page,
        itemsPerPage: perPage,
        pageStart: total === 0 ? 0 : (page - 1) * perPage,
        pageStop: Math.min(page * perPage, total),
        pageCount: Math.ceil(total / perPage),
        itemsLength: total
      };
    },
    groupOptions() {
      return {
        page: this.groupPage || 1,
        itemsPerPage: this.groupSize || this.pageSize
      };
    },
    onUpdateGroupOptions(opts) {
      if (opts.page) {
        this.groupPage = opts.page;
      }
      if (opts.itemsPerPage && opts.itemsPerPage !== this.groupSize) {
        this.groupSize = opts.itemsPerPage;
        this.groupPage = 1;
      }
    },
    groupIcon(group) {
      var os = (group.os_type || '').toLowerCase();
      if (os.indexOf('ios') !== -1 || os.indexOf('iphone') !== -1) return 'mdi-apple-ios';
      if (os.indexOf('mac') !== -1)     return 'mdi-laptop-mac';
      if (os.indexOf('android') !== -1) return 'mdi-android';
      if (os.indexOf('windows') !== -1) return 'mdi-microsoft-windows';
      return 'mdi-monitor-cellphone';
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
