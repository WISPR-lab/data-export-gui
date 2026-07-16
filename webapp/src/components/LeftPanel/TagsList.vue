<!--
Copyright 2023 Google Inc. All rights reserved.

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
  <div>
    <div>
      <v-data-iterator
        no-data-text=""
        :items="nonZeroItems"
        :items-per-page.sync="itemsPerPage"
        :search="search"
        :hide-default-footer="nonZeroItems.length <= itemsPerPage"
      >
        <template v-slot:header v-if="nonZeroItems.length > itemsPerPage">
          <v-toolbar flat>
            <v-text-field
              v-model="search"
              clearable
              hide-details
              outlined
              dense
              prepend-inner-icon="mdi-magnify"
              label="Search for tags ..."
            ></v-text-field>
          </v-toolbar>
        </template>
        <template v-slot:default="props">
          <div
            v-for="item in props.items"
            :key="item.tag || item.label"
            @click="applyFilterChip(item.tag || item.label, item.tag ? 'tag' : '', item.tag ? 'tag' : 'label')"
            style="cursor: pointer; font-size: 0.9em"
          >
            <v-row no-gutters class="pa-2 pl-5" :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'">
              <v-icon v-if="item.label === 'starred'" left small color="amber">mdi-star</v-icon>
              <v-icon v-if="item.label === '__ts_comment'" left small>mdi-comment-multiple-outline</v-icon>
              <v-icon v-if="getQuickTag(item.tag)" small left :color="getQuickTag(item.tag).color">{{ getQuickTag(item.tag).label }}</v-icon>
              <span>
                {{ (item.tag || item.label) | formatLabelText }} (<small><strong>{{ item.count | compactNumber }}</strong></small>)
              </span>
            </v-row>
          </div>
        </template>
      </v-data-iterator>
    </div>

    <!-- Zero-count items shown below divider only after filter search has executed -->
    <template v-if="zeroItems.length">
      <v-divider class="my-2 mx-3"></v-divider>
      <div
        v-for="item in zeroItems"
        :key="'zero-' + (item.tag || item.label)"
        @click="applyFilterChip(item.tag || item.label, item.tag ? 'tag' : '', item.tag ? 'tag' : 'label')"
        class="text--secondary"
        style="cursor: pointer; font-size: 0.9em;"
      >
        <v-row no-gutters class="pa-2 pl-5" :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'">
          <v-icon v-if="item.label === 'starred'" left small color="amber">mdi-star</v-icon>
          <v-icon v-if="item.label === '__ts_comment'" left small>mdi-comment-multiple-outline</v-icon>
          <v-icon v-if="getQuickTag(item.tag)" small left :color="getQuickTag(item.tag).color">{{ getQuickTag(item.tag).label }}</v-icon>
          <span>
            {{ (item.tag || item.label) | formatLabelText }} (<small><strong>0</strong></small>)
          </span>
        </v-row>
      </div>
    </template>
  </div>
</template>

<script>
import EventBus from '../../event-bus.js'

export default {
  data: function () {
    return {
      // TODO: Refactor this into a configurable option
      quickTags: [
        { tag: 'bad', color: 'red', textColor: 'white', label: 'mdi-alert-circle-outline' },
        { tag: 'suspicious', color: 'orange', textColor: 'white', label: 'mdi-help-circle-outline' },
        { tag: 'good', color: 'green', textColor: 'white', label: 'mdi-check-circle-outline' },
      ],
      itemsPerPage: 10,
      search: '',
      isFiltered: false,
      filteredCounts: {},
    }
  },
  mounted() {
    EventBus.$on('searchResultsCounts', this.onSearchResultsCounts)
  },
  beforeDestroy() {
    EventBus.$off('searchResultsCounts', this.onSearchResultsCounts)
  },
  computed: {
    meta() {
      return this.$store.state.meta
    },
    tags() {
      return this.$store.state.tags
    },
    labels() {
      return this.meta.filter_labels || []
    },
    customTags() {
      return this.tags.filter((tag) => !this.getQuickTag(tag.tag))
    },
    assignedQuickTags() {
      return this.tags.filter((tag) => this.getQuickTag(tag.tag))
    },
    nonZeroItems() {
      var self = this
      return this.allTagsAndLabels
        .map(function(item) {
          var key = item.tag || item.label
          var count = self.isFiltered ? (self.filteredCounts[key] || 0) : item.count
          return Object.assign({}, item, { count: count })
        })
        .filter(function(item) { return item.count > 0 })
    },
    zeroItems() {
      if (!this.isFiltered) return []
      var self = this
      return this.allTagsAndLabels
        .map(function(item) {
          var key = item.tag || item.label
          var count = self.isFiltered ? (self.filteredCounts[key] || 0) : item.count
          return Object.assign({}, item, { count: count })
        })
        .filter(function(item) { return item.count === 0 })
    },
    allTagsAndLabels() {
      const safeLabels = Array.isArray(this.labels) ? this.labels : []
      return [...safeLabels, ...this.assignedQuickTags, ...this.customTags]
        .filter(item => item.tag || item.label)
        .filter(item => !(item.label && item.label.startsWith('__ts_fact')))
        .sort((a, b) => {
          const aLabel = a.tag || a.label
          const bLabel = b.tag || b.label

          if (aLabel === 'starred') return -1
          if (bLabel === 'starred') return 1

          return aLabel.localeCompare(bLabel)
        })
    },
  },
  watch: {
    nonZeroItems: function(val) {
      this.$emit('filtered-count', this.isFiltered ? val.length : null)
    },
    labels: {
      handler(newLabels) {
        var self = this
        newLabels.forEach(function(item) {
          var key = item.label || item.tag
          if (self.isFiltered) {
            self.$set(self.filteredCounts, key, item.count)
          }
        })
      },
      deep: true
    },
    tags: {
      handler(newTags) {
        var self = this
        newTags.forEach(function(item) {
          var key = item.label || item.tag
          if (self.isFiltered) {
            self.$set(self.filteredCounts, key, item.count)
          }
        })
      },
      deep: true
    }
  },
  methods: {
    getQuickTag(tag) {
      return this.quickTags.find((el) => el.tag === tag)
    },
    onSearchResultsCounts(payload) {
      this.filteredCounts = payload.countPerTagOrLabel || {}
      this.isFiltered = true
    },
    applyFilterChip(term, termField='', termType='label') {
      let eventData = {}
      eventData.doSearch = true
      // Don't set queryString for chip-based filters - the chip does the filtering
      let chip = {
        field: termField,
        value: term,
        type: termType,
        operator: 'must',
        active: true,
      }
      eventData.chip = chip
      EventBus.$emit('setQueryAndFilter', eventData)
      if (this.$route.name !== 'Events' && this.$route.name !== 'DemoEvents') {
        const target = this.$store.state.demoMode ? '/demo/events' : '/events'
        this.$router.push(target)
      }
    },
  },
}
</script>
