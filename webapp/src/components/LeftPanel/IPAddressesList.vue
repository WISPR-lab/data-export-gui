<template>
  <div>
    <v-data-iterator
      :items="ipAddresses"
      :items-per-page.sync="itemsPerPage"
      :hide-default-footer="ipAddresses.length <= itemsPerPage"
    >
      <template v-slot:default="props">
        <div
          v-for="item in props.items"
          :key="item.ip_address"
          @click="applyFilterChip(item.ip_address)"
          style="cursor: pointer; font-size: 0.9em"
        >
          <v-row no-gutters class="pa-2 pl-5" :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'">
            <span
              >{{ item.ip_address }} (<small
                ><strong>{{ item.count | compactNumber }}</strong></small
              >)</span
            >
          </v-row>
        </div>
      </template>
    </v-data-iterator>
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
    }
  },
  async mounted() {
    try {
      this.ips = await DB.getIPAddresses()
    } catch (e) {
      console.error('Error loading IP addresses:', e)
      this.ips = []
    }
  },
  computed: {
    ipAddresses() {
      return [...this.ips]
    },
  },
  methods: {
    applyFilterChip(ip_address) {
      let eventData = {}
      eventData.doSearch = true
      eventData.queryString = 'client_ip:' + '"' + ip_address + '"'
      EventBus.$emit('setQueryAndFilter', eventData)
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
