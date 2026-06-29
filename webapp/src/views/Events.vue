<!--
Copyright 2021 Google Inc. All rights reserved.

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

<!-- NOTICE --- MODIFIED FOR WISPR-lab/data-export-gui -->


<template>
  <v-container fluid>
    <!-- Right side menu -->
    <!-- Placeholder at the moment. Keeping it here for quick developement later. -->

    <!-- Search and Filters -->
    <v-card flat class="pa-3 pt-0 mt-n3" color="transparent">
      <search-bar
        v-model="currentQueryString"
        @search="handleSearchBarSearch"
      ></search-bar>

      <!-- Search History -->
      <div class="mt-4">
        <v-card v-show="showSearchHistory" outlined>
          <v-toolbar dense flat>
            <v-toolbar-title>Search history</v-toolbar-title>
            <v-spacer></v-spacer>
            <v-slider
              v-model="zoomLevel"
              thumb-label
              ticks
              append-icon="mdi-magnify-plus-outline"
              prepend-icon="mdi-magnify-minus-outline"
              min="0.1"
              max="1"
              step="0.1"
              class="mt-6"
            >
              <template v-slot:thumb-label="{ value }"> {{ value * 100 }}% </template>
            </v-slider>

            <v-btn icon @click="showSearchHistory = false" class="ml-4">
              <v-icon title="Close search history">mdi-close</v-icon>
            </v-btn>
          </v-toolbar>

          <v-divider></v-divider>

          <div
            v-dragscroll
            class="pa-md-4 no-scrollbars"
            style="overflow: scroll; white-space: nowrap; max-height: 500px; min-height: 100px"
          >
            <!-- <search-history-tree
              @node-click="jumpInHistory"
              :show-history="showSearchHistory"
              v-bind:style="{ transform: 'scale(' + zoomLevel + ')' }"
              style="transform-origin: top left"
            ></search-history-tree> -->
          </div>
        </v-card>
      </div>

      <!-- Search help dialog has been moved to SearchBar component -->


      <!-- Data export picker -->
      <div>
        <v-toolbar flat dense style="background-color: transparent" class="mt-n3">
          <v-btn small icon @click="showDataExports = !showDataExports">
            <v-icon v-if="showDataExports" title="Hide Data Exports">mdi-chevron-up</v-icon>
            <v-icon v-else title="Show Data Exports">mdi-chevron-down</v-icon>
          </v-btn>
          <span class="data-export-header">
            <new-data-export-button btn-type="small"></new-data-export-button>
            <v-dialog v-model="addManualEvent" width="600">
              <template v-slot:activator="{ on, attrs }">
                <!-- <v-btn small text rounded color="primary" v-bind="attrs" v-on="on">
                  <v-icon left small> mdi-plus </v-icon>
                  Add manual event
                </v-btn> -->
              </template>
              <ts-add-manual-event
                app
                @cancel="addManualEvent = false"
                :datetimeProp="datetimeManualEvent"
              ></ts-add-manual-event>
            </v-dialog>
            <v-btn small text rounded color="primary" @click.stop="enableAllDataExports()">
              <v-icon left small>mdi-eye</v-icon>
              <span>Select all</span>
            </v-btn>
            <v-btn small text rounded color="primary" @click.stop="disableAllDataExports()">
              <v-icon left small>mdi-eye-off</v-icon>
              <span>Unselect all</span>
            </v-btn>
          </span>
        </v-toolbar>
        <v-expand-transition>
          <div v-show="showDataExports">
            <data-export-picker
              id="dataExportPicker"
              :current-query-filter="currentQueryFilter"
              :count-per-index="countPerIndex"
              :count-per-data-export="countPerDataExport"
            ></data-export-picker>
          </div>
        </v-expand-transition>
      </div>

      <!-- Filters area -->
      <div data-filter-id="demo-filters">
        <!-- Time filter chips -->
        <div>
          <span v-for="(chip, index) in timeFilterChips" :key="index + chip.value">
            <filter-chip
              :chip="chip"
              @remove="removeChip"
              @toggle="toggleChip"
              @update="updateChip"
            ></filter-chip>
            <v-btn v-if="index + 1 < timeFilterChips.length" icon small style="margin-top: 2px" class="mr-2">OR</v-btn>
          </span>
          <span>
            <v-menu
              v-model="timeFilterMenu"
              offset-y
              :close-on-content-click="false"
              :close-on-click="true"
              content-class="menu-with-gap"
              allow-overflow
              style="overflow: visible"
            >
              <template v-slot:activator="{ on, attrs }">
                <v-btn small text rounded color="primary" id="tsAddTimefilterButton" v-bind="attrs" v-on="on">
                  <v-icon left small> mdi-clock-plus-outline </v-icon>
                  Add timefilter
                </v-btn>
              </template>

              <filter-menu app @cancel="timeFilterMenu = false" @addChip="addChip"></filter-menu>
            </v-menu>
          </span>
        </div>

        <!-- Term filters -->
        <div v-if="filterChips.length" class="mt-1">
          <v-chip-group column>
            <span v-for="(chip, index) in filterChips" :key="index + chip.value">
              <filter-chip
                :chip="chip"
                @remove="removeChip"
                @toggle="toggleChip"
                @toggle-operator="toggleChipOperator"
              ></filter-chip>
            </span>
          </v-chip-group>
        </div>
      </div>
    </v-card>

    <!-- Eventlist -->
    <v-card flat class="mt-5 mx-3" color="transparent">
      <event-list
        id="tsEventList"
        :query-request="activeQueryRequest"
        @countPerIndex="updateCountPerIndex($event)"
        @countPerDataExport="updateCountPerDataExport($event)"
      ></event-list>
    </v-card>
  </v-container>
</template>

<script>
import EventBus from '../event-bus.js'

import { dragscroll } from 'vue-dragscroll'

import DataExportPicker from '../components/Events/DataExportPicker.vue'
import FilterMenu from '../components/Events/FilterMenu.vue'
import NewDataExportButton from '../components/Import/NewDataExportButton.vue'
import TsAddManualEvent from '../components/Events/AddManualEvent.vue'
import EventList from '../components/Events/EventList.vue'
import SearchBar from '../components/Events/SearchBar.vue'
import FilterChip from '../components/Events/FilterChip.vue'

const defaultQueryFilter = () => {
  return {
    from: 0,
    terminate_after: 40,
    size: 40,
    uploadIds: '_all',
    order: 'asc',
    chips: [],
  }
}

export default {
  directives: {
    dragscroll,
  },
  components: {
    DataExportPicker,
    FilterMenu,
    NewDataExportButton,
    TsAddManualEvent,
    EventList,
    SearchBar,
    FilterChip,
  },
  props: ['projectId'],
  data() {
    return {
      countPerIndex: {},
      countPerDataExport: {},
      currentItemsPerPage: 40,
      timeFilterMenu: false,
      selectedFields: [{ field: 'message', type: 'text' }],
      showRightSidePanel: false,
      addManualEvent: false,
      datetimeManualEvent: '',
      params: {},
      contextEvent: false,
      originalContext: false,
      activeQueryRequest: {},
      currentQueryString: '',
      currentQueryFilter: defaultQueryFilter(),
      selectedLabels: [],
      showSearchHistory: false,

      zoomLevel: 0.7,
      zoomOrigin: {
        x: 0,
        y: 0,
      },
      // TODO: Refactor this into a configurable option
      quickTags: [
        { tag: 'bad', color: 'red', textColor: 'white', label: 'mdi-alert-circle-outline' },
        { tag: 'suspicious', color: 'orange', textColor: 'white', label: 'mdi-help-circle-outline' },
        { tag: 'good', color: 'green', textColor: 'white', label: 'mdi-check-circle-outline' },
      ],
      showDataExports: true,
    }
  },
  computed: {
    project() {
      return this.$store.state.project
    },
    enabledDataExports() {
      return this.$store.state.enabledDataExports
    },
    meta() {
      return this.$store.state.meta
    },
    filterChips: function () {
      return this.currentQueryFilter.chips.filter((chip) => chip && chip.type && (chip.type === 'label' || chip.type === 'term' || chip.type === 'tag'))
    },
    timeFilterChips: function () {
      return this.currentQueryFilter.chips.filter((chip) => chip && chip.type && chip.type.startsWith('datetime'))
    },
    demoMode() {
      return this.$store.state.demoMode
    },
    tourWasOffered() {
      return this.$store.state.tourWasOffered
    },
    hasDataExports() {
      return !!(this.project.dataExports && this.project.dataExports.length)
    },
    filteredLabels() {
      return this.$store.state.meta.filter_labels.filter((label) => label && typeof label.label === 'string' && !label.label.startsWith('__'))
    },
    currentSearchNode() {
      return this.$store.state.currentSearchNode
    },
    activeContext() {
      return this.$store.state.activeContext
    },
    allDataExports() {
      let dataExports = [...this.project.dataExports]
      return dataExports.sort(function (a, b) {
        return a.name.localeCompare(b.name)
      })
    },
    uploadState() {
      return this.$store.state.uploadState
    },
  },
  watch: {
    enabledDataExports: function () {
      this.updateEnabledDataExports(this.enabledDataExports)
    },
    hasDataExports(newVal) {
      if (newVal && this.$route.name === 'DemoEvents') {
        console.log('[Events] Data loaded for DemoEvents, auto-starting demo');
        this.$nextTick(() => {
          this.startDemo();
        });
      }
    },
    $route(to) {
      if (to.name === 'DemoEvents' && this.hasDataExports) {
        console.log('[Events] Route changed to DemoEvents, auto-starting demo');
        this.$nextTick(() => {
          this.startDemo();
        });
      }
    },
  },
  methods: {
    getQuickTag(tag) {
      return this.quickTags.find((el) => el.tag === tag)
    },
    startDemo() {
      console.log('[Events] Starting interactive demo');
      const DemoController = require('@/demo/DemoController.js').default
      DemoController.start(this.$store)
    },
    updateCountPerIndex: function (count) {
      this.countPerIndex = count
    },
    updateCountPerDataExport: function (count) {
      this.countPerDataExport = count
    },
    toggleSearchHistory: function () {
      this.showSearchHistory = !this.showSearchHistory
      if (this.showSearchHistory) {
        this.triggerScrollTo()
      }
    },
    setQueryAndFilter: function (searchEvent) {
      const isDemo = this.$route.name === 'DemoEvents' || this.$route.name === 'DemoDevices'
      if (this.$route.name !== 'Events' && !isDemo) {
        this.$router.push({ name: 'Events', params: { projectId: this.project.id } })
      }
      if (searchEvent.queryString) {
        this.currentQueryString = searchEvent.queryString
      }

      if (!searchEvent.queryFilter) {
        searchEvent.queryFilter = this.currentQueryFilter
      }
      this.currentQueryFilter = searchEvent.queryFilter

      if (searchEvent.chip) {
        const chipExist = this.currentQueryFilter.chips.find(function (chip) {
          return chip.field === searchEvent.chip.field && chip.value === searchEvent.chip.value
        })
        if (!chipExist) {
          this.currentQueryFilter.chips.push(searchEvent.chip)
        }
      }

      this.currentQueryFilter.size = this.currentItemsPerPage
      this.currentQueryFilter.terminate_after = this.currentItemsPerPage

      if (searchEvent.doSearch) {
        if (searchEvent.incognito) {
          this.search(true, true)
        } else {
          this.search()
        }
      }
    },

    search: function (resetPagination = true, incognito = false, parent = false) {
      let queryRequest = {}
      queryRequest['queryString'] = this.currentQueryString
      queryRequest['queryFilter'] = this.currentQueryFilter
      queryRequest['resetPagination'] = resetPagination
      queryRequest['incognito'] = incognito
      queryRequest['parent'] = parent
      this.activeQueryRequest = queryRequest
      if (this.$store.state.demoMode) {
        EventBus.$emit('demo:action', 'search-executed')
      }
    },
    handleSearchBarSearch(event) {
      this.currentQueryString = event.queryString
      if (event.promotedChips && event.promotedChips.length > 0) {
        if (!this.currentQueryFilter.chips) {
          this.currentQueryFilter.chips = []
        }
        event.promotedChips.forEach(function (chip) {
          const exists = this.currentQueryFilter.chips.some(function (c) {
            return c.field === chip.field && c.value === chip.value && c.type === chip.type && c.operator === chip.operator
          })
          if (!exists) {
            this.currentQueryFilter.chips.push(chip)
          }
        }.bind(this))
      }
      this.search()
    },
    // searchView: function (viewId) {
    //   this.showSearchDropdown = false

    //   if (this.$route.name !== 'Events') {
    //     this.$router.push({ name: 'Events', params: { projectId: this.project.id } })
    //   }

    //   if (viewId !== parseInt(viewId, 10) && typeof viewId !== 'string') {
    //     viewId = viewId.id
    //   }

    //   BrowserDB.getView(this.projectId, viewId)
    //     .then((response) => {
    //       let view = response.data.objects[0]
    //       this.currentQueryString = view.query_string
    //       this.currentQueryFilter = JSON.parse(view.query_filter)
    //       if (!this.currentQueryFilter.fields || !this.currentQueryFilter.fields.length) {
    //         this.currentQueryFilter.fields = [{ field: 'message', type: 'text' }]
    //       }
    //       this.selectedFields = this.currentQueryFilter.fields
    //       let chips = this.currentQueryFilter.chips
    //       if (chips) {
    //         for (let i = 0; i < chips.length; i++) {
    //           if (chips[i].type === 'label') {
    //             this.selectedLabels.push(chips[i].value)
    //           }
    //         }
    //       }
    //       this.contextEvent = false
    //       this.search()
    //     })
    //     .catch((e) => {})
    // },
    searchContext: function (event) {
      // TODO: Make this selectable in the UI
      const contextTime = 300
      const numContextEvents = 500

      this.contextEvent = event
      if (!this.originalContext) {
        let currentQueryStringCopy = JSON.parse(JSON.stringify(this.currentQueryString))
        let currentQueryFilterCopy = JSON.parse(JSON.stringify(this.currentQueryFilter))
        this.originalContext = { queryString: currentQueryStringCopy, queryFilter: currentQueryFilterCopy }
      }

      const dateTimeTemplate = 'YYYY-MM-DDTHH:mm:ss[Z]'
      let startDateTimeMoment = this.$moment.utc(this.contextEvent._source.datetime)
      let newStartDate = startDateTimeMoment.clone().subtract(contextTime, 's').format(dateTimeTemplate)
      let newEndDate = startDateTimeMoment.clone().add(contextTime, 's').format(dateTimeTemplate)
      let startChip = {
        field: '',
        value: newStartDate + ',' + startDateTimeMoment.format(dateTimeTemplate),
        type: 'datetime_range',
        operator: 'must',
        active: true,
      }
      let endChip = {
        field: '',
        value: startDateTimeMoment.format(dateTimeTemplate) + ',' + newEndDate,
        type: 'datetime_range',
        operator: 'must',
        active: true,
      }
      // TODO: Use chips instead
      this.currentQueryString = '* OR ' + '_id:' + this.contextEvent._id

      this.currentQueryFilter.chips = [startChip, endChip]

      // Use data_export_id from event source (browser model doesn't have indices_metadata)
      const dataExportId = this.contextEvent._source.data_export_id || this.contextEvent._source.__ts_data_export_id
      if (dataExportId) {
        this.currentQueryFilter.uploadIds = [dataExportId]
      }
      this.currentQueryFilter.size = numContextEvents
      this.search()
    },
    removeContext: function () {
      this.contextEvent = false
      this.currentQueryString = JSON.parse(JSON.stringify(this.originalContext.queryString))
      this.currentQueryFilter = JSON.parse(JSON.stringify(this.originalContext.queryFilter))
      this.search()
    },
    updateEnabledDataExports: function (dataExportIds) {
      this.currentQueryFilter.uploadIds = dataExportIds
      this.search()
    },
    toggleChip: function (chip) {
      // Treat undefined as active to support old chip formats.
      if (chip.active === undefined) {
        chip.active = true
      }
      chip.active = !chip.active
      this.search()
    },
    toggleChipOperator: function (chip) {
      if (chip.operator === 'must_not') {
        chip.operator = 'must'
      } else {
        chip.operator = 'must_not'
      }
      this.search()
    },


    removeChip: function (chip, search = true) {
      let chipIndex = this.currentQueryFilter.chips.findIndex((c) => c.value === chip.value)
      this.currentQueryFilter.chips.splice(chipIndex, 1)
      if (chip.type === 'label') {
        this.selectedLabels = this.selectedLabels.filter((label) => label !== chip.value)
      }
      if (search) {
        this.search()
      }
    },
    updateChip: function (newChip, oldChip) {
      // Replace the chip at the given index
      let chipIndex = this.currentQueryFilter.chips.findIndex(
        (c) => c.value === oldChip.value && c.type === oldChip.type
      )
      this.currentQueryFilter.chips.splice(chipIndex, 1, newChip)
      this.search()
    },
    addChip: function (chip) {
      // Legacy views don't support chips so we need to add an array in order
      // to upgrade the view to the new filter system.
      if (!this.currentQueryFilter.chips) {
        this.currentQueryFilter.chips = []
      }
      this.currentQueryFilter.chips.push(chip)
      this.search()
    },
    addChipFromHistogram: function (chip) {
      if (!this.currentQueryFilter.chips) {
        this.currentQueryFilter.chips = []
      }
      this.currentQueryFilter.chips.forEach((chip) => {
        if (chip.type === 'datetime_range') {
          this.removeChip(chip, false)
        }
      })
      this.addChip(chip)
    },
    toggleLabelChip: function (labelName) {
      let chip = {
        field: '',
        value: labelName,
        type: 'label',
        operator: 'must',
        active: true,
      }
      let chips = this.currentQueryFilter.chips
      if (chips) {
        for (let i = 0; i < chips.length; i++) {
          if (chips[i].value === labelName) {
            this.removeChip(i)
            return
          }
        }
      }
      this.addChip(chip)
    },
    updateLabelChips: function () {
      // Remove all current label chips
      this.currentQueryFilter.chips = this.currentQueryFilter.chips.filter((chip) => chip.type !== 'label')
      this.selectedLabels.forEach((label) => {
        let chip = {
          field: '',
          value: label,
          type: 'label',
          operator: 'must',
          active: true,
        }
        this.addChip(chip)
        this.showSearchDropdown = false
      })
    },
    updateLabelList: function (label) {
      if (this.meta.filter_labels.indexOf(label) === -1) {
        this.meta.filter_labels.push(label)
      }
    },
    jumpInHistory: function (node) {
      this.currentQueryString = node.query_string
      this.currentQueryFilter = JSON.parse(node.query_filter)
      if (!this.currentQueryFilter.fields || !this.currentQueryFilter.fields.length) {
        this.currentQueryFilter.fields = [{ field: 'message', type: 'text' }]
      }
      this.selectedFields = this.currentQueryFilter.fields
      if (this.currentQueryFilter.uploadIds[0] === '_all' || this.currentQueryFilter.uploadIds === '_all') {
        // Dexie-native: just use timeline IDs
        let allIds = this.project.dataExports.map(dataExport => dataExport.id)
        this.currentQueryFilter.uploadIds = allIds
      }
      let chips = this.currentQueryFilter.chips
      if (chips) {
        for (let i = 0; i < chips.length; i++) {
          if (chips[i].type === 'label') {
            this.selectedLabels.push(chips[i].value)
          }
        }
      }
      this.contextEvent = false
      this.search(true, true, node.id)
    },
    triggerScrollTo: function () {
      EventBus.$emit('triggerScrollTo')
    },
    zoomWithMouse: function (event) {
      // Add @wheel="zoomWithMouse" on element to activate.
      this.zoomOrigin.x = event.pageX
      this.zoomOrigin.y = event.pageY
      if (event.deltaY < 0) {
        this.zoomLevel += 0.07
      } else if (event.deltaY > 0) {
        this.zoomLevel -= 0.07
      }
    },
    closeSearchDropdown: function (targetElement) {
      // Prevent dropdown to close when the search input field is clicked.
      if ((!this.$refs.searchInput || targetElement !== this.$refs.searchInput) && targetElement.getAttribute('data-explore-element') === null) {
        this.showSearchDropdown = false
      }
    },
    onClickOutside: function (e) {
      if (e.target.id !== 'tsSearchInput') {
        this.showSearchDropdown = false
      }
    },
    enableAllDataExports() {
      this.$store.dispatch(
        'updateEnabledDataExports',
        this.allDataExports.map((tl) => tl.id)
      )
    },
    disableAllDataExports() {
      this.$store.dispatch('updateEnabledDataExports', [])
    },
  },
  mounted() {
    EventBus.$on('setQueryAndFilter', this.setQueryAndFilter)
    
    // Auto-start demo if in DemoEvents route
    if (this.$route.name === 'DemoEvents' && this.hasDataExports) {
      console.log('[Events] Auto-starting demo on mount');
      this.$nextTick(() => {
        this.startDemo();
      });
    }
  },
  beforeDestroy() {
    EventBus.$off('setQueryAndFilter')
    EventBus.$off('setActiveView')
  },
  created: function () {
    let doSearch = false

    this.params = {
      viewId: this.$route.query.view,
      exportId: this.$route.query.export || this.$route.query.timeline,
      resultLimit: this.$route.query.limit,
      queryString: this.$route.query.q,
    }

    // if (this.params.viewId) {
    //   this.searchView(this.params.viewId)
    //   return
    // }

    if (this.params.queryString) {
      this.currentQueryString = this.params.queryString
      doSearch = true
    }

    if (this.params.exportId) {
      if (!this.params.queryString) {
        this.currentQueryString = '*'
      }

      let dataExport = this.project.dataExports.find((dataExport) => {
        return dataExport.id === parseInt(this.params.exportId, 10)
      })
      if (dataExport) {
        this.currentQueryFilter.uploadIds = [dataExport.id]
      }
      doSearch = true
    }

    if (!this.currentQueryString) {
      this.currentQueryFilter.uploadIds = ['_all']
    }

    if (doSearch) {
      if (!this.currentQueryFilter.uploadIds.length) {
        this.currentQueryFilter.uploadIds = ['_all']
      }
      this.search()
    }
  },
}
</script>

<style lang="scss">
.chip-disabled {
  text-decoration: line-through;
  opacity: 0.5;
}

.chip-operator-label {
  margin-right: 7px;
  font-size: 0.7em;
  cursor: default;
}

.no-scrollbars::-webkit-scrollbar {
  display: none;
}

.no-scrollbars {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.filter-chip-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 400px;
}

.expanded .data-export-header {
  .v-icon.open-indicator {
    display: inline;
  }
  .v-icon.closed-indicator {
    display: none;
  }
}
.data-export-header {
  display: flex;
  align-items: center;

  .v-icon.open-indicator {
    display: none;
  }
}
</style>
