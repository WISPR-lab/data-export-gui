<!--
Copyright 2025 Google Inc. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

<!--NOTICE --- MODIFIED FOR WISPR-lab/data-export-gui -->

<template>
  <div id="tsLeftPanelEventTypesList">
    <v-data-iterator
       no-data-text=""
      :items="nonZeroItems"
      :items-per-page.sync="itemsPerPage"
      :search="search"
      :hide-default-footer="nonZeroItems.length <= itemsPerPage"
    >

      <template v-slot:default="props">
        <div
          v-for="msg in props.items"
          :key="msg.event_type_msg"
          @click="setQueryAndFilter(msg.event_type_msg)"
          style="cursor: pointer; font-size: 0.9em"
        >
          <v-row no-gutters class="pa-2 pl-5" :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'">
            <span>{{ msg.event_type_msg }} (<small><strong>{{ msg.count | compactNumber }}</strong></small>)</span>
          </v-row>
        </div>
      </template>
    </v-data-iterator>

    <!-- Zero-count items after a query filtered them out -->
    <template v-if="zeroItems.length">
      <v-divider class="my-2 mx-3"></v-divider>
      <div
        v-for="msg in zeroItems"
        :key="'zero-' + msg.event_type_msg"
        @click="setQueryAndFilter(msg.event_type_msg)"
        class="text--secondary"
        style="cursor: pointer; font-size: 0.9em;"
      >
        <v-row no-gutters class="pa-2 pl-5" :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'">
          <span>{{ msg.event_type_msg }} (<small><strong>0</strong></small>)</span>
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
      search: '',
      event_types: [],
      seenKeys: {}, // tracks types ever seen with count>0
      isFiltered: false,
    }
  },
  async mounted() {
    await this.loadEventTypes()
    EventBus.$on('searchResultsCounts', this.onSearchResultsCounts)
  },
  beforeDestroy() {
    EventBus.$off('searchResultsCounts', this.onSearchResultsCounts)
  },
  computed: {
    project() {
      return this.$store.state.project
    },
    eventTypes() {
      return [...this.event_types].sort(function(a, b) { return a.event_type_msg.localeCompare(b.event_type_msg) })
    },
    nonZeroItems() {
      return this.eventTypes.filter(function(t) { return t.count > 0 })
    },
    zeroItems() {
      // Only show zero-count items if a query is active and they were previously seen
      if (!this.isFiltered) return []
      var self = this
      var nonZeroKeys = {}
      this.nonZeroItems.forEach(function(t) { nonZeroKeys[t.event_type_msg] = true })
      return Object.keys(self.seenKeys)
        .filter(function(k) { return !nonZeroKeys[k] })
        .map(function(k) { return { event_type_msg: k, count: 0 } })
        .sort(function(a, b) { return a.event_type_msg.localeCompare(b.event_type_msg) })
    },
  },
  watch: {
    project: {
      async handler() {
        await this.loadEventTypes()
      },
      deep: true
    },
    nonZeroItems: function(val) {
      this.$emit('filtered-count', this.isFiltered ? val.length : null)
    },
  },
  methods: {
    async loadEventTypes() {
      try {
        this.event_types = await DB.getEventTypes()
        var self = this
        this.event_types.forEach(function(t) {
          if (t.count > 0) self.seenKeys[t.event_type_msg] = true
        })
        this.isFiltered = false
        this.$emit('filtered-count', null)
      } catch (e) {
        console.error('Error loading event actions:', e)
        this.event_types = []
      }
    },
    onSearchResultsCounts(payload) {
      const countMap = payload.countPerEventType || {}
      var self = this
      var merged = Object.keys(self.seenKeys).map(function(k) {
        return { event_type_msg: k, count: countMap[k] || 0 }
      })
      Object.keys(countMap).forEach(function(k) {
        if (!self.seenKeys[k]) {
          merged.push({ event_type_msg: k, count: countMap[k] })
          self.seenKeys[k] = true
        }
      })
      this.event_types = merged
      this.isFiltered = true
    },
    setQueryAndFilter(action) {
      let eventData = {}
      eventData.doSearch = true
      eventData.chip = {
        field: 'event_type_msg',
        value: action,
        type: 'attribute',
        operator: 'must',
        active: true,
      }
      EventBus.$emit('setQueryAndFilter', eventData)
      if (this.$store.state.demoMode) {
        EventBus.$emit('demo:action', 'event-type-clicked')
      }
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
