<template>
  <div>
    <v-data-iterator
      :items="nonZeroItems"
      :items-per-page.sync="itemsPerPage"
      :hide-default-footer="nonZeroItems.length <= itemsPerPage"
    >
      <template v-slot:default="props">
        <div
          v-for="item in props.items"
          :key="item.client_ip"
          class="ip-row"
          :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'"
          style="position: relative; font-size: 0.9em; cursor: pointer;"
          @click="applyFilterChip(item.client_ip)"
        >
          <v-row no-gutters class="pa-2 pl-5">
            <span>{{ item.client_ip }} (<small><strong>{{ item.count | compactNumber }}</strong></small>)</span>
          </v-row>
          <!-- row action menu (geolocate/add tag) disabled pending IP table work - see openTagDialog/noopPersist/onTagChanged below
          <v-menu offset-y>
            <template v-slot:activator="{ on, attrs }">
              <v-btn
                icon small
                :ripple="false"
                class="ip-row-action"
                :class="{ 'ip-row-action--visible': attrs['aria-expanded'] === 'true' }"
                v-bind="attrs" v-on="on"
                @click.stop
              >
                <v-icon>mdi-dots-vertical</v-icon>
              </v-btn>
            </template>
            <v-list dense>
              <v-list-item disabled>
                <v-list-item-icon class="mr-2"><v-icon small>mdi-map-marker-outline</v-icon></v-list-item-icon>
                <v-list-item-content>Geolocate</v-list-item-content>
                <v-chip x-small class="ml-2">Coming soon</v-chip>
              </v-list-item>
              <v-list-item @click="openTagDialog(item)">
                <v-list-item-icon class="mr-2"><v-icon>mdi-tag-plus-outline</v-icon></v-list-item-icon>
                <v-list-item-content>Add tag</v-list-item-content>
              </v-list-item>
            </v-list>
          </v-menu>
          -->
        </div>
      </template>
    </v-data-iterator>

    <!-- Zero-count IPs after a query filtered them out -->
    <template v-if="zeroItems.length">
      <v-divider class="my-2 mx-3"></v-divider>
      <div
        v-for="item in zeroItems"
        :key="'zero-' + item.client_ip"
        @click="applyFilterChip(item.client_ip)"
        class="text--secondary"
        style="cursor: pointer; font-size: 0.9em;"
      >
        <v-row no-gutters class="pa-2 pl-5" :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'">
          <span>{{ item.client_ip }} (<small><strong>0</strong></small>)</span>
        </v-row>
      </div>
    </template>

    <!--
    <v-dialog v-model="tagDialog.open" max-width="500px">
      <event-tag-dialog
        v-if="tagDialog.open"
        :events="[{ _source: { tags: [] } }]"
        :persist="noopPersist"
        silent
        @close="tagDialog.open = false"
        @tag-added="onTagChanged($event, false)"
        @tag-removed="onTagChanged($event, true)"
      />
    </v-dialog>
    -->
  </div>
</template>

<script>
import EventBus from '../../event-bus.js'
import DB from '@/database/index.js'
// import EventTagDialog from '../Events/EventTagDialog.vue' // row action menu disabled pending IP table work

export default {
  // components: { EventTagDialog },
  props: [],
  data: function () {
    return {
      itemsPerPage: 10,
      ips: [],
      seenKeys: {},
      isFiltered: false,
      tagDialog: { open: false, ip: null },
    }
  },
  async mounted() {
    try {
      this.ips = await DB.getIPAddresses(this.$route.meta.dbName || 'userdata')
      var self = this
      this.ips.forEach(function(ip) { if (ip.count > 0) self.seenKeys[ip.client_ip] = true })
      this.$emit('filtered-count', null)
    } catch (e) {
      console.error('Error loading IP addresses:', e)
      this.ips = []
    }
    EventBus.$on('searchResultsCounts', this.onSearchResultsCounts)
  },
  beforeDestroy() {
    EventBus.$off('searchResultsCounts', this.onSearchResultsCounts)
  },
  computed: {
    project() {
      return this.$store.state.project
    },
    ipAddresses() {
      return [...this.ips]
    },
    nonZeroItems() {
      return this.ipAddresses.filter(function(ip) { return ip.count > 0 })
    },
    zeroItems() {
      if (!this.isFiltered) return []
      var self = this
      var nonZeroKeys = {}
      this.nonZeroItems.forEach(function(ip) { nonZeroKeys[ip.client_ip] = true })
      return Object.keys(self.seenKeys)
        .filter(function(k) { return !nonZeroKeys[k] })
        .map(function(k) { return { client_ip: k, count: 0 } })
        .sort(function(a, b) { return a.client_ip.localeCompare(b.client_ip) })
    },
  },
  watch: {
    'project.dataExports': {
      async handler() {
        try {
          this.ips = await DB.getIPAddresses(this.$route.meta.dbName || 'userdata')
          var self = this
          this.ips.forEach(function(ip) { if (ip.count > 0) self.seenKeys[ip.client_ip] = true })
          this.isFiltered = false
          this.$emit('filtered-count', null)
        } catch (e) {
          console.error('Error reloading IP addresses:', e)
        }
      },
      deep: true
    },
    nonZeroItems: function(val) {
      this.$emit('filtered-count', this.isFiltered ? val.length : null)
    },
  },
  methods: {
    onSearchResultsCounts(payload) {
      const countMap = payload.countPerIPAddress || {}
      var self = this
      var merged = Object.keys(self.seenKeys).map(function(k) {
        return { client_ip: k, count: countMap[k] || 0 }
      })
      Object.keys(countMap).forEach(function(k) {
        if (!self.seenKeys[k]) {
          merged.push({ client_ip: k, count: countMap[k] })
          self.seenKeys[k] = true
        }
      })
      this.ips = merged
      this.isFiltered = true
    },
    applyFilterChip(clientIp) {
      let eventData = {}
      eventData.doSearch = true
      eventData.chip = {
        field: 'client_ip',
        value: clientIp,
        type: 'attribute',
        operator: 'must',
        active: true,
      }
      EventBus.$emit('setQueryAndFilter', eventData)
      if (this.$route.name !== 'Events' && this.$route.name !== 'DemoEvents') {
        const target = this.$store.state.demoMode ? '/demo/events' : '/events'
        this.$router.push(target)
      }
    },
    openTagDialog(item) {
      this.tagDialog = { open: true, ip: item.client_ip }
    },
    noopPersist() {
      return Promise.resolve()
    },
    async onTagChanged(tag, remove) {
      if (!this.tagDialog.ip) return
      const changedCount = await DB.addTagToEventsQuery(this.$route.meta.dbName || 'userdata', `client_ip:"${this.tagDialog.ip}"`, tag, remove)
      if (changedCount) {
        this.$store.dispatch('updateEventLabels', { label: tag, num: remove ? -changedCount : changedCount })
      }
    },
  },
}
</script>

<style scoped lang="scss">
.ip-row-action {
  position: absolute;
  top: 50%;
  right: 8px;
  transform: translateY(-50%);
  opacity: 0;
  transition: opacity 0.15s ease;
  box-shadow: none !important;
}
.ip-row-action::before {
  background: transparent !important;
}
.ip-row-action ::v-deep .v-icon {
  color: rgba(0, 0, 0, 0.4);
  transition: color 0.15s ease;
}
.ip-row-action:hover ::v-deep .v-icon {
  color: rgba(0, 0, 0, 0.7);
}
.ip-row:hover .ip-row-action,
.ip-row-action--visible {
  opacity: 1;
}

.v-text-field ::v-deep input {
  font-size: 0.9em;
}

.v-text-field ::v-deep label {
  font-size: 0.9em;
}

::v-deep .v-data-footer__icons-before .v-btn,
::v-deep .v-data-footer__icons-after .v-btn {
  width: 28px;
  height: 28px;
}

::v-deep .v-data-footer__icons-before .v-icon,
::v-deep .v-data-footer__icons-after .v-icon {
  font-size: 1rem;
}

::v-deep .v-data-footer__pagination {
  margin-left: 15px !important;
  margin-right: 15px !important;
}
</style>
