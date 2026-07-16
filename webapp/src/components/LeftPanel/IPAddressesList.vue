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
          @click="applyFilterChip(item.client_ip)"
          style="cursor: pointer; font-size: 0.9em"
        >
          <v-row no-gutters class="pa-2 pl-5" :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'">
            <span>{{ item.client_ip }} (<small><strong>{{ item.count | compactNumber }}</strong></small>)</span>
          </v-row>
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
  </div>
</template>

<script>
import EventBus from '../../event-bus.js'
import DB from '@/database/index.js'

export default {
  props: [],
  data: function () {
    return {
      itemsPerPage: 10,
      ips: [],
      // ponytail: seenKeys tracks IPs ever seen with count>0; used to show zero-count items after filtering
      seenKeys: {},
      isFiltered: false,
    }
  },
  async mounted() {
    try {
      this.ips = await DB.getIPAddresses()
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
        type: 'term',
        operator: 'must',
        active: true,
      }
      EventBus.$emit('setQueryAndFilter', eventData)
      if (this.$route.name !== 'Events' && this.$route.name !== 'DemoEvents') {
        const target = this.$store.state.demoMode ? '/demo/events' : '/events'
        this.$router.push(target)
      }
    },
  },
}
</script>

<style scoped lang="scss">
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
