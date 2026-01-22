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
<template>
  <div>
    <v-alert
      v-model="showBanner"
      dense
      dismissible
      type="info"
    >
      Data may be incomplete. Some timelines are still loading.
    </v-alert>

    <v-dialog v-model="exportDialog" width="700">
      <v-card flat class="pa-5">
        <v-progress-circular indeterminate size="20" width="1"></v-progress-circular>
        <span class="ml-5">Exporting {{ totalHits }} events</span>
      </v-card>
    </v-dialog>

    <v-dialog v-model="saveSearchMenu" v-if="!disableSaveSearch" width="500">
      <v-card class="pa-4">
        <h3>Save Search</h3>
        <br />
        <v-text-field
          clearable
          v-model="saveSearchFormName"
          required
          placeholder="Name your saved search"
          outlined
          dense
          autofocus
          @focus="$event.target.select()"
          :rules="saveSearchNameRules"
        >
        </v-text-field>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="saveSearchMenu = false"> Cancel </v-btn>
          <v-btn
            text
            color="primary"
            @click="saveSearch"
            :disabled="!saveSearchFormName || saveSearchFormName.length > 255"
          >
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <div v-if="!eventList.objects.length && !searchInProgress && !currentQueryString">
      <ts-explore-welcome-card></ts-explore-welcome-card>
    </div>

    <div v-if="!eventList.objects.length && !searchInProgress && currentQueryString" class="ml-3">
      <ts-search-not-found-card
        :currentQueryString="currentQueryString"
        :filterChips="filterChips"
        :disableSaveSearch="disableSaveSearch"
        @save-search-clicked="saveSearchMenu = true"
      ></ts-search-not-found-card>
    </div>

    <!-- DISABLED: Row highlighting feature
    <div v-if="highlightEvent" class="mt-4">
      <strong>Showing context for event:</strong>
      <v-sheet class="d-flex flex-wrap mt-1 mb-5">
        <v-sheet class="flex-1-0">
          <span style="width: 200px" v-bind:style="getTimelineColor(highlightEvent)" class="datetime-table-cell pa-2">
            <span v-if="(highlightEvent._source.primary_timestamp !== null && highlightEvent._source.primary_timestamp !== '') || (highlightEvent._source.timestamp !== null && highlightEvent._source.timestamp !== '')">
              {{ highlightEvent._source.primary_timestamp | formatTimestamp | toISO8601 }}
            </span>
            <span v-else style="font-style: italic">undated</span>
          </span>
        </v-sheet>

        <v-sheet class="">
          <span class="datetime-table-cell pa-2">
            {{ highlightEvent._source.message }}
          </span>
        </v-sheet>
      </v-sheet>
    </div>
    -->

    <div class="ts-event-list-container">
      <v-card
        v-if="(eventList.objects.length > 0 || searchInProgress) && userSettings.eventSummarization && !eventList.meta.summaryError"
        class="ts-ai-summary-card"
        outlined
      >
        <v-card-title class="ts-ai-summary-card-title">
          <v-btn icon small @click="toggleSummary" class="ts-ai-summary-fold-btn">
            <v-icon>{{ summaryCollapsed ? 'mdi-chevron-down' : 'mdi-chevron-up' }}</v-icon>
          </v-btn>
          <v-icon small color="primary" class="ml-1 mr-2 ts-ai-summary-icon">mdi-shimmer</v-icon>
          <div class="ts-ai-summary-text-group">
            <span class="ts-ai-summary-title">AI Summary</span>
            <span v-if="eventList.objects.length > 0" class="ts-ai-summary-subtitle">
              (for {{ eventList.objects.length }} events in this view)
            </span>
          </div>
          <v-btn icon small class="ml-1 ts-ai-summary-info-btn" :title="summaryInfoMessage">
            <v-icon small>mdi-information-outline</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text v-show="!summaryCollapsed" class="ts-ai-summary-text">
          <div v-if="isSummaryLoading || !eventList.meta.summary">
            <div class="ts-summary-placeholder-line shimmer"></div>
            <div class="ts-summary-placeholder-line shimmer short"></div>
            <div class="ts-summary-placeholder-line shimmer long"></div>
          </div>
          <div v-else v-html="eventList.meta.summary"></div>
        </v-card-text>

      </v-card>
    </div>


    <div v-if="eventList.objects.length || searchInProgress">
      <v-data-table
        v-model="selectedEvents"
        :headers="headers"
        :items="eventList.objects"
        :footer-props="{ 'items-per-page-options': [10, 40, 80, 100, 200, 500], 'show-current-page': true }"
        :loading="searchInProgress"
        :options.sync="tableOptions"
        :server-items-length="totalHitsForPagination"
        item-key="_id"
        loading-text="Searching... Please wait"
        show-select
        disable-filtering
        must-sort
        :sort-desc.sync="sortOrderAsc"
        @update:sort-desc="sortEvents"
        sort-by="_source.timestamp"
        :hide-default-footer="totalHits < 11 || disablePagination"
        :expanded="expandedRows"
        :dense="displayOptions.isCompact"
        fixed-header
      >
          <template v-slot:top="{ pagination, options, updateOptions }">
            <v-toolbar dense flat color="transparent">
              <div v-if="!selectedEvents.length">
                <span style="display: inline-block; min-width: 200px">
                  <small>{{ fromEvent }}-{{ toEvent }} of {{ totalHits }} events ({{ totalTime }}s)</small>
                </span>

                <template>
                  <v-btn icon @click="saveSearchMenu = true" v-if="!disableSaveSearch">
                    <v-icon title="Save current search">mdi-content-save-outline</v-icon>
                  </v-btn>
                </template>

                <template>
                  <v-btn icon @click="showHistogram = !showHistogram" v-if="!disableHistogram">
                    <v-icon title="Toggle event histogram">mdi-chart-bar</v-icon>
                  </v-btn>
                </template>

                <v-dialog v-model="columnDialog" v-if="!disableColumns" max-width="500px" scrollable>
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn icon v-bind="attrs" v-on="on">
                      <v-icon title="Modify columns">mdi-view-column-outline</v-icon>
                    </v-btn>
                  </template>

                  <v-card height="50vh">
                    <v-card-title>Select columns</v-card-title>

                    <v-card-text>
                      <v-text-field
                        v-model="searchColumns"
                        append-icon="mdi-magnify"
                        label="Search"
                        single-line
                        hide-details
                      ></v-text-field>
                      <br />
                      <v-data-table
                        v-model="selectedFields"
                        :headers="columnHeaders"
                        :items="meta.mappings"
                        :search="searchColumns"
                        :hide-default-footer="true"
                        item-key="field"
                        disable-pagination
                        show-select
                        dense
                        @input="updateSelectedFields"
                      >
                      </v-data-table>
                    </v-card-text>

                    <v-divider></v-divider>

                    <v-card-actions>
                      <v-spacer></v-spacer>
                      <v-btn text @click="selectedFields = [{ field: 'message', type: 'text' }]"> Reset </v-btn>
                      <v-btn text color="primary" @click="columnDialog = false"> Set columns </v-btn>
                    </v-card-actions>
                  </v-card>
                </v-dialog>

                <v-btn icon @click="exportSearchResult()">
                  <v-icon title="Download current view as CSV">mdi-download</v-icon>
                </v-btn>

                <v-menu v-if="!disableSettings" offset-y :close-on-content-click="false">
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn icon v-bind="attrs" v-on="on">
                      <v-icon title="View settings">mdi-dots-horizontal</v-icon>
                    </v-btn>
                  </template>

                  <v-card outlined max-width="475" class="mx-auto">
                    <v-list subheader two-line flat dense>
                      <v-subheader>Density</v-subheader>

                      <v-list-item-group>
                        <v-list-item :ripple="false">
                          <template>
                            <v-list-item-action>
                              <v-radio-group v-model="displayOptions.isCompact">
                                <v-radio :value="false"></v-radio>
                              </v-radio-group>
                            </v-list-item-action>

                            <v-list-item-content>
                              <v-list-item-title>Comfortable</v-list-item-title>
                              <v-list-item-subtitle>More space between rows</v-list-item-subtitle>
                            </v-list-item-content>
                          </template>
                        </v-list-item>

                        <v-list-item :ripple="false">
                          <template>
                            <v-list-item-action>
                              <v-radio-group v-model="displayOptions.isCompact">
                                <v-radio :value="true"></v-radio>
                              </v-radio-group>
                            </v-list-item-action>

                            <v-list-item-content>
                              <v-list-item-title>Compact</v-list-item-title>
                              <v-list-item-subtitle>Less space between rows</v-list-item-subtitle>
                            </v-list-item-content>
                          </template>
                        </v-list-item>
                      </v-list-item-group>
                      <v-divider></v-divider>

                      <v-list subheader two-line flat>
                        <v-subheader>Misc</v-subheader>
                        <v-list-item-group>
                          <v-list-item :ripple="false">
                            <v-list-item-action>
                              <v-switch dense color="" v-model="displayOptions.showTags"></v-switch>
                            </v-list-item-action>
                            <v-list-item-content>
                              <v-list-item-title>Tags</v-list-item-title>
                              <v-list-item-subtitle>Show tags</v-list-item-subtitle>
                            </v-list-item-content>
                          </v-list-item>
                        </v-list-item-group>
                        <v-list-item-group>
                          <v-list-item :ripple="false">
                            <v-list-item-action>
                              <v-switch dense v-model="displayOptions.showEmojis"></v-switch>
                            </v-list-item-action>
                            <v-list-item-content>
                              <v-list-item-title>Emojis</v-list-item-title>
                              <v-list-item-subtitle>Show emojis</v-list-item-subtitle>
                            </v-list-item-content>
                          </v-list-item>
                        </v-list-item-group>
                        <v-list-item-group>
                          <v-list-item :ripple="false">
                            <v-list-item-action>
                              <v-switch dense v-model="displayOptions.showTimelineName"></v-switch>
                            </v-list-item-action>
                            <v-list-item-content>
                              <v-list-item-title>Timeline name</v-list-item-title>
                              <v-list-item-subtitle>Show timeline name</v-list-item-subtitle>
                            </v-list-item-content>
                          </v-list-item>
                        </v-list-item-group>
                      </v-list>
                    </v-list>
                  </v-card>
                </v-menu>
              </div>
              <div v-else class="actions">
                <small class="mr-2">Actions:</small>
                <v-btn x-small outlined @click="toggleMultipleStars()">
                  <v-icon left color="amber">mdi-star</v-icon>
                  Toggle star
                </v-btn>

                <v-menu v-model="showEventTagMenu" offset-x :close-on-content-click="false">
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn x-small outlined v-bind="attrs" v-on="on">
                      <v-icon left>mdi-tag-plus-outline</v-icon>
                      Modify Tags
                    </v-btn>
                  </template>

                  <ts-event-tag-dialog :events="selectedEvents" @close="showEventTagMenu = false"></ts-event-tag-dialog>

                </v-menu>
              </div>

              <v-spacer></v-spacer>

              <v-data-footer
                v-if="totalHits > 11 && !disablePagination"
                :pagination="pagination"
                :options="options"
                @update:options="updateOptions"
                :show-current-page="true"
                :items-per-page-options="[10, 40, 80, 100, 200, 500]"
                items-per-page-text="Rows per page:"
                style="border: 0"
                class="mr-n3"
              ></v-data-footer>
            </v-toolbar>

            <v-card v-if="showHistogram" outlined class="my-3">
              <v-toolbar dense flat color="transparent">
                <v-spacer></v-spacer>
                <v-btn v-if="timeFilterChips.length" text color="primary" @click="removeChips(timeFilterChips)">
                  reset
                </v-btn>
                <v-btn icon @click="showHistogram = false">
                  <v-icon title="Close histogram">mdi-close</v-icon>
                </v-btn>
              </v-toolbar>
              <ts-bar-chart
                :chart-data="eventList.meta.count_over_time"
                @addChip="addChipFromHistogram($event)"
              ></ts-bar-chart>
            </v-card>
          </template>

          <!-- Event details -->
          <template v-slot:expanded-item="{ headers, item }">
            <td :colspan="headers.length">
              <!-- Details -->
              <v-container v-if="item.showDetails" fluid class="mt-4">
                <ts-event-detail :event="item"></ts-event-detail>
              </v-container>

              <!-- Time bubble -->
              <v-divider v-if="item.showDetails && item.deltaDays"></v-divider>
              <div v-if="item.deltaDays > 0" class="ml-7">
                <div
                  class="ts-time-bubble-vertical-line ts-time-bubble-vertical-line-color"
                  v-bind:style="getTimeBubbleColor(item)"
                ></div>
                <div class="ts-time-bubble ts-time-bubble-color" v-bind:style="getTimeBubbleColor(item)">
                  <div class="ts-time-bubble-text">
                    <b>{{ item.deltaDays | compactNumber }}</b> days
                  </div>
                </div>
                <div
                  class="ts-time-bubble-vertical-line ts-time-bubble-vertical-line-color"
                  v-bind:style="getTimeBubbleColor(item)"
                ></div>
              </div>
            </td>
          </template>

          <!-- Actions field -->
          <template v-slot:item.actions="{ item }">
            <v-btn small icon @click="toggleStar(item)">
              <v-icon title="Toggle star status" v-if="item._source.labels && item._source.labels.includes('__ts_star')" color="amber"
                >mdi-star</v-icon
              >
              <v-icon title="Toggle star status" v-else>mdi-star-outline</v-icon>
            </v-btn>

            <!-- Tag menu -->
            <ts-event-tag-menu :event="item"></ts-event-tag-menu>

            <!-- Action sub-menu -->
            <ts-event-action-menu :event="item" @showContextWindow="showContextWindow($event)"></ts-event-action-menu>
          </template>

          <!-- Datetime field with action buttons -->
          <template v-slot:item._source.primary_timestamp="{ item }">
            <!-- <div v-bind:style="getTimelineColor(item)" class="datetime-table-cell"> -->
            <div class="datetime-table-cell">
              <span v-if="(item._source.primary_timestamp !== null && item._source.primary_timestamp !== '')">
                <!-- {{ item._source.primary_timestamp }} -->
                <!-- {{ (item._source.primary_timestamp | formatTimestamp | shortDateTime ) }} -->
                  {{ $options.filters.shortDateTimeLocal(item._source.primary_timestamp) }}
              </span>
              <span v-else style="font-style: italic">undated</span>
            </div>
          </template>

          <!-- Generic slot for any field type. Adds tags and emojis to the first column. -->
          <template v-for="(field, index) in headers" v-slot:[getFieldName(field.text)]="{ item }">
            <div
              :key="field.text"
              class="ts-event-field-container"
              style="cursor: pointer"
              @click="toggleDetailedEvent(item)"
            >
              <span
                :class="{
                  // 'ts-event-field-ellipsis': field.text === 'category',
                  'ts-event-field-highlight': item._id === highlightEventId, 
                }"
              >
                <!-- Tags -->
                <span
                  v-if="
                    displayOptions.showTags &&
                    // index === 3 &&
                    (field.text === 'category' || (index === 4 && headers[3].value === '_source.comment')) &&
                    (item._source.tags && item._source.tags.length > 0)
                  "
                >
                  <ts-event-tags :item="item" :tagConfig="tagConfig" :showDetails="item.showDetails"></ts-event-tags>
                </span>
                <!-- Emojis -->
                <span v-if="displayOptions.showEmojis && (field.text === 'category' || (index === 4 && headers[3].value === '_source.comment')) && item._source.__ts_emojis">
                <!-- <span v-if="displayOptions.showEmojis && index === 3 && item._source.__ts_emojis"> -->
                  <span
                    class="mr-2"
                    v-for="emoji in item._source.__ts_emojis"
                    :key="emoji"
                    v-html="emoji + ';'"
                    :title="meta.emojis && meta.emojis[emoji]"
                  >
                  </span>
                </span>
                <!-- <span>{{ item._source[field.text] }} hihihih {{ field.text }} </span> -->
                <span>{{ field.text === 'category' ? $options.filters.categoryName(item._source[field.text]) : item._source[field.text] }}</span>
                <!-- <span>{{ field.text === 'category' ? $options.filters.categoryName(item._source[field.text]) : item._source[field.text] }}</span> -->
              </span>
            </div>
          </template>

          <!-- Timeline name field -->
          <template v-slot:item.timeline_name="{ item }">
            <!-- <v-chip label style="margin-top: 1px; margin-bottom: 1px; font-size: 0.8em"> -->
            <v-chip label style="margin-top: 1px; margin-bottom: 1px; font-size: 0.8em" v-bind:style="getTimelineColor(item)">
              <span class="timeline-name-ellipsis" style="width: 130px; text-align: center">{{
                getTimeline(item).name
              }}</span></v-chip>
          </template>

          <!-- Comment field -->
          <template v-slot:item._source.comment="{ item }">
            <div class="d-inline-block">
              <v-btn icon small @click="toggleDetailedEvent(item)" v-if="item._source.comment && item._source.comment.length">
                <v-badge :offset-y="10" :offset-x="10" bordered :content="item._source.comment.length">
                  <v-icon :title="item['showDetails'] ? 'Close event &amp; comments' : 'Open event &amp; comments'" small>
                    mdi-comment-text-multiple-outline
                  </v-icon>
                </v-badge>
              </v-btn>
            </div>

            <div v-if="item['showDetails'] && (!item._source.comment || !item._source.comment.length) && !item.showComments" class="d-inline-block">
              <v-btn icon small @click="newComment(item)">
                <v-icon title="Add a comment"> mdi-comment-plus-outline </v-icon>
              </v-btn>
            </div>

            <div v-if="item['showDetails'] && (!item._source.comment || !item._source.comment.length) && item.showComments" class="d-inline-block">
              <v-btn icon small @click="item.showComments = false">
                <v-icon title="Close comments"> mdi-comment-remove-outline </v-icon>
              </v-btn>
            </div>
          </template>
        </v-data-table>
      </div>
    </div>
</template>

<script>
import BrowserDB from '../../database.js'
import EventBus from '../../event-bus.js'

import TsBarChart from './BarChart.vue'
import TsEventDetail from './EventDetail.vue'
import TsEventTagMenu from './EventTagMenu.vue'
import TsEventTagDialog from './EventTagDialog.vue'
import TsEventActionMenu from './EventActionMenu.vue'
import TsEventTags from './EventTags.vue'
import TsExploreWelcomeCard from './ExploreWelcomeCard.vue'
import TsSearchNotFoundCard from './SearchNotFoundCard.vue'

const defaultQueryFilter = () => {
  return {
    from: 0,
    terminate_after: 40,
    size: 40,
    indices: ['_all'],
    order: 'desc',
    chips: [],
  }
}

const emptyEventList = () => {
  return {
    meta: {
      count_per_timeline: {},
      num_events: 0,
      num_states: 0,
      has_next_page: false,
    },
    objects: [],
  }
}

export default {
  components: {
    TsBarChart,
    TsEventDetail,
    TsEventTagMenu,
    TsEventTagDialog,
    TsEventActionMenu,
    TsEventTags,
    TsExploreWelcomeCard,
    TsSearchNotFoundCard,
  },
  props: {
    queryRequest: {
      type: Object,
      default: () => {},
    },
    itemsPerPage: {
      type: Number,
      default: 40,
    },
    disableSaveSearch: {
      type: Boolean,
      default: false,
    },
    disableHistogram: {
      type: Boolean,
      default: true,
    },
    disableColumns: {
      type: Boolean,
      default: false,
    },
    disableSettings: {
      type: Boolean,
      default: false,
    },
    disablePagination: {
      type: Boolean,
      default: false,
    },
    highlightEvent: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      showEventTagMenu: false,
      columnHeaders: [
        {
          text: '',
          value: 'field',
        },
      ],
      tableOptions: {
        itemsPerPage: this.itemsPerPage,
      },
      isSummaryLoading: false,
      currentItemsPerPage: this.itemsPerPage,
      expandedRows: [],
      selectedFields: [{ field: 'category', type: 'text' }],
      searchColumns: '',
      columnDialog: false,
      saveSearchMenu: false,
      saveSearchFormName: '',
      saveSearchNameRules: [(v) => !!v || 'Name is required.', (v) => (v && v.length <= 255) || 'Name is too long.'],
      selectedEventTags: [],
      tagConfig: {
        good: { color: 'green', textColor: 'white', label: 'mdi-check-circle-outline' },
        bad: { color: 'red', textColor: 'white', label: 'mdi-alert-circle-outline' },
        suspicious: { color: 'orange', textColor: 'white', label: 'mdi-help-circle-outline' },
      },
      searchInProgress: false,
      exportDialog: false,
      currentPage: 1,
      eventList: {
        meta: {},
        objects: [],
      },
      currentQueryString: '',
      currentQueryFilter: defaultQueryFilter(),
      selectedEvents: [],
      displayOptions: {
        isCompact: false,
        showTags: true,
        showEmojis: true,
        showMillis: false,
        showTimelineName: true,
      },
      showHistogram: false,
      branchParent: null,
      sortOrderAsc: true,
      summaryCollapsed: false,
      showBanner: false,
    }
  },
  computed: {
    summaryInfoMessage() {
      const totalEvents = this.eventList.meta.summary_event_count
      const uniqueEvents = this.eventList.meta.summary_unique_event_count
      return `[experimental] This summary is based on the message field on your current page (${totalEvents} rows, ${uniqueEvents} unique message fields).`
    },
    sketch() {
      return this.$store.state.sketch
    },
    meta() {
      return this.$store.state.meta
    },
    highlightEventId() {
      if (this.highlightEvent) {
        return this.highlightEvent._id
      }
      return null
    },
    totalHits() {
      // Use total_count from metadata (represents ALL matching events, not just current page)
      return this.eventList.meta.total_count || 0;
    },
    totalHitsForPagination() {
      // Return actual total hits from the database
      // Vuetify uses this for the "1-100 of X" display
      return this.totalHits;
    },
    totalTime() {
      return this.eventList.meta.query_time_ms / 1000 || 0
    },
    fromEvent() {
      return this.currentQueryFilter.from || 1
    },
    toEvent() {
      if (this.totalHits < this.currentQueryFilter.size) {
        return
      }
      return parseInt(this.currentQueryFilter.from) + parseInt(this.currentQueryFilter.size)
    },
    timeFilterChips: function () {
      return this.currentQueryFilter.chips.filter((chip) => chip.type.startsWith('datetime'))
    },
    currentSearchNode() {
      return this.$store.state.currentSearchNode
    },
    userSettings() {
      return this.$store.state.settings
    },
    headers() {
      let baseHeaders = [
        {
          text: '',
          value: 'data-table-select',
          sortable: false,
        },
        {
          value: 'actions',
          width: '105',
          sortable: false,
        },
        {
          text: `Datetime (${this.$store.state.localTimezoneAbbr}) `,
          align: 'start',
          value: '_source.primary_timestamp',
          width: '200',
          sortable: true,
        },
        {
          value: '_source.comment',
          width: '40',
          sortable: false,
        },
      ]
      let extraHeaders = []
      this.selectedFields.forEach((field) => {
        let header = {
          text: field.field,
          align: 'start',
          value: '_source.' + field.field,
          sortable: false,
        }
        if (field.field === 'message') {
          header.width = '100%'
          extraHeaders.unshift(header)
        } else {
          extraHeaders.push(header)
        }
      })

      // Extend the column headers from position 3 (after the actions column)
      baseHeaders.splice(3, 0, ...extraHeaders)

      // Add timeline name based on configuration
      if (this.displayOptions.showTimelineName) {
        baseHeaders.push({
          value: 'timeline_name',
          align: 'end',
          sortable: false,
        })
      }
      // console.log('[EventList.headers] Generated headers:', baseHeaders)
      return baseHeaders
    },
    activeContext() {
      return this.$store.state.activeContext
    },
    settings() {
      return this.$store.state.settings
    },
    filterChips: function () {
      return this.currentQueryFilter.chips.filter((chip) => chip.type === 'label' || chip.type === 'term')
    },
  },
  methods: {
    toggleSummary() {
          this.summaryCollapsed = !this.summaryCollapsed;
          localStorage.setItem('aiSummaryCollapsed', String(this.summaryCollapsed));
    },
    sortEvents(sortDesc) {
      // sortDesc is the value of Vuetify's sort-desc (true = descending, false = ascending)
      if (sortDesc) {
        this.currentQueryFilter.order = 'desc'
      } else {
        this.currentQueryFilter.order = 'asc'
      }
      this.search(true, true, false)
    },
    getFieldName: function (field) {
      return 'item._source.' + field
    },
    toggleDetailedEvent: function (row) {
      let index = this.expandedRows.findIndex((x) => x._id === row._id)
      if (this.expandedRows.some((event) => event._id === row._id)) {
        if (row.showDetails) {
          row['showDetails'] = false
          this.expandedRows.splice(index, 1)
          this.$set(row, 'showComments', false)
        } else {
          row['showDetails'] = true
          this.expandedRows.splice(index, 1)
          this.expandedRows.push(row)
          return
        }

        if (row.deltaDays) {
          this.expandedRows.splice(index, 1)
          this.expandedRows.push(row)
        }
      } else {
        row['showDetails'] = true
        this.expandedRows.push(row)
      }
    },
    newComment: function (row) {
      if (row.showDetails) {
        this.$set(row, 'showComments', true)
      } else {
        this.$set(row, 'showComments', true)
        this.toggleDetailedEvent(row)
      }
    },
    addTimeBubbles: function () {
      this.expandedRows = []
      this.eventList.objects.forEach((event, index) => {
        if (index < 1) {
          return
        }
        let prevEvent = this.eventList.objects[index - 1]
        let timestampMillis = this.$options.filters.formatTimestamp(event._source.primary_timestamp)
        let prevTimestampMillis = this.$options.filters.formatTimestamp(prevEvent._source.primary_timestamp)
        let timestamp = Math.floor(timestampMillis / 1000)
        let prevTimestamp = Math.floor(prevTimestampMillis / 1000)
        let delta = Math.floor(timestamp - prevTimestamp)
        // In descending order (most recent first), prevEvent has later timestamp, so flip the delta
        if (this.currentQueryFilter.order === 'desc') {
          delta = Math.floor(prevTimestamp - timestamp)
        }
        let deltaDays = Math.floor(delta / 60 / 60 / 24)
        if (deltaDays > 0) {
          prevEvent['deltaDays'] = deltaDays
          this.expandedRows.push(prevEvent)
        }
      })
    },
    getTimeline: function (event) {
      // Browser model: events have timeline_id directly
      const timelineId = event._source.timeline_id
      const timeline = this.sketch.timelines.find((tl) => tl.id === timelineId)
      if (!timeline) {
        console.warn('[EventList.getTimeline] Timeline not found for id:', timelineId)
        return { name: 'Unknown Timeline', id: timelineId, color: '#999' }
      }
      return timeline
    },
    getTimelineColor(event) {
      let timeline = this.getTimeline(event)
      let backgroundColor = timeline.color
      if (!backgroundColor.startsWith('#')) {
        backgroundColor = '#' + backgroundColor
      }
      if (this.$vuetify.theme.dark) {
        return {
          'background-color': backgroundColor,
          filter: 'grayscale(25%)',
          color: '#333',
        }
      }
      return {
        'background-color': backgroundColor,
      }
    },
    getTimeBubbleColor() {
      let backgroundColor = '#f5f5f5'
      if (this.$vuetify.theme.dark) {
        backgroundColor = '#333'
      }
      return {
        'background-color': backgroundColor,
      }
    },
    getAllIndices: function () {
      // Browser model: return timeline IDs directly
      return this.sketch.timelines.map((tl) => tl.id)
    },
    search: async function (resetPagination = true, incognito = false, parent = false) {
      console.log('[EventList.search] Called with queryString:', this.currentQueryString, 'indices:', this.currentQueryFilter.indices)
      
      // Exit early if there are no indices selected
      if (this.currentQueryFilter.indices && !this.currentQueryFilter.indices.length) {
        console.log('[EventList.search] No indices selected, exiting')
        this.eventList = emptyEventList()
        return
      }

      // Expand '_all' to all timeline IDs (handle both array ['_all'] and string '_all')
      const indices = this.currentQueryFilter.indices;
      if (
        indices === '_all' || 
        (Array.isArray(indices) && (indices.length === 0 || indices[0] === '_all'))
      ) {
        const allIndices = this.getAllIndices();
        this.currentQueryFilter.indices = allIndices;
        console.log('[EventList.search] Expanded _all to timelines:', this.currentQueryFilter.indices);
      }

      // Allow searches with empty query string (shows all events from selected timelines)
      // if (!this.currentQueryString) {
      //   console.log('[EventList.search] No query string, exiting')
      //   return
      // }

      this.searchInProgress = true
      this.selectedEvents = []
      this.eventList = emptyEventList()

      if (resetPagination) {
        this.tableOptions.page = 1
        this.currentPage = 1
        this.currentItemsPerPage = this.tableOptions.itemsPerPage
        this.currentQueryFilter.size = this.tableOptions.itemsPerPage
        this.currentQueryFilter.from = 0
      }

      const startTime = Date.now()
      
      try {
        // Use BrowserDB.search() with our query string and filter
        const formData = {
          query: this.currentQueryString,
          filter: this.currentQueryFilter,
        }
        
        console.log('[EventList.search] Calling BrowserDB.search with formData:', formData)
        const response = await BrowserDB.search(this.sketch.id, formData)
        // console.log('[EventList.search] Got response:', response)
        console.log('[EventList.search] response.data.objects:', response.data.objects)

        // Response should have:
        // - data.objects: array of {_id, _source} wrapped events
        // - data.meta: metadata including count_per_timeline, has_next_page, etc.
        this.eventList.objects = response.data.objects || []
        this.eventList.meta = response.data.meta || {
          count_per_timeline: {},
          num_events: 0,
          num_states: 0,
          has_next_page: false,
          query_time_ms: Date.now() - startTime
        }

        console.log('[EventList.search] Updated eventList.objects length:', this.eventList.objects.length)
        this.updateShowBanner()
        this.$emit('countPerTimeline', this.eventList.meta.count_per_timeline)
        EventBus.$emit('updateCountPerTimeline', this.eventList.meta.count_per_timeline)
        
        this.addTimeBubbles()
        // console.log('[EventList.search] addTimeBubbles complete')
      } catch (error) {
        console.error('[EventList.search] Error searching events:', error)
        this.errorSnackBar('Error fetching search results: ' + error.message)
      } finally {
        this.searchInProgress = false
        console.log('[EventList.search] searchInProgress is now:', this.searchInProgress)
      }
    },
    // fetchEventSummary: function() {
    //   const formData = {
    //     query: this.currentQueryString,
    //     filter: this.currentQueryFilter,
    //   }
    //   BrowserDB.llmRequest(this.sketch.id, 'llm_summarize', formData)
    //     .then((response) => {
    //       this.$set(this.eventList.meta, 'summary', response.data.response)
    //       this.$set(this.eventList.meta, 'summary_event_count', response.data.summary_event_count)
    //       this.$set(this.eventList.meta, 'summary_unique_event_count', response.data.summary_unique_event_count)
    //       this.isSummaryLoading = false
    //     })
    //     .catch((error) => {
    //       console.error("Error fetching event summary:", error)
    //       this.$set(this.eventList.meta, 'summaryError', true)
    //       this.isSummaryLoading = false
    //     })
    // },
    exportSearchResult: function () {
      // TODO: Implement CSV export for browser model
      this.exportDialog = false
    },
    addChip: function (chip) {
      if (!this.currentQueryFilter.chips) {
        this.currentQueryFilter.chips = []
      }
      this.currentQueryFilter.chips.push(chip)
      this.search()
    },
    removeChip: function (chip, search = true) {
      let chipIndex = this.currentQueryFilter.chips.findIndex((c) => c.value === chip.value)
      this.currentQueryFilter.chips.splice(chipIndex, 1)
      if (search) {
        this.search()
      }
    },
    removeChips: function (chips, search = true) {
      if (!Array.isArray(chips)) {
        this.errorSnackBar('Not an array of chips')
        return
      }
      chips.forEach((chip) => {
        this.removeChip(chip, false)
      })
      if (search) {
        this.search()
      }
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
    paginate: function () {
      // Reset pagination if number of pages per page changes.
      if (this.tableOptions.itemsPerPage !== this.currentItemsPerPage) {
        this.tableOptions.page = 1
        this.currentPage = 1
        this.currentItemsPerPage = this.tableOptions.itemsPerPage
        this.currentQueryFilter.size = this.tableOptions.itemsPerPage
        this.search(true, true)
        return
      }
      // To avoid double search request exit early if this is the first search for this
      // search session.
      if (this.currentPage === this.tableOptions.page) {
        return
      }
      this.currentQueryFilter.from =
        this.tableOptions.page * this.currentQueryFilter.size - this.currentQueryFilter.size
      this.currentPage = this.tableOptions.page
      this.search(false, true)
    },
    updateSelectedFields: function (value) {
      // If we haven't fetched the field before, do an new search.
      value.forEach((field) => {
        if (!this.headers.filter((e) => e.field === field.field).length > 0) {
          this.search(true, true)
        }
      })
    },
    removeField: function (index) {
      this.selectedFields.splice(index, 1)
    },
    toggleStar(event) {
      // Ensure labels array exists
      if (!event._source.labels) {
        event._source.labels = []
      }
      
      // Determine if we're adding or removing the star
      const isStarred = event._source.labels.includes('__ts_star');
      
      if (isStarred) {
        event._source.labels.splice(event._source.labels.indexOf('__ts_star'), 1)
        BrowserDB.removeLabelEvent([event._id], ['__ts_star']).catch(e => {
          console.error('Error updating star in database:', e)
        })
      } else {
        event._source.labels.push('__ts_star')
        BrowserDB.addLabelEvent([event._id], ['__ts_star']).catch(e => {
          console.error('Error updating star in database:', e)
        })
      }
    },
    toggleMultipleStars: function () {
      let netStarCountChange = 0
      const eventsToStar = []
      const eventsToUnstar = []
      
      this.selectedEvents.forEach((event) => {
        // Ensure labels array exists
        if (!event._source.labels) {
          event._source.labels = []
        }
        if (event._source.labels.includes('__ts_star')) {
          event._source.labels.splice(event._source.labels.indexOf('__ts_star'), 1)
          eventsToUnstar.push(event._id)
          netStarCountChange--
        } else {
          event._source.labels.push('__ts_star')
          eventsToStar.push(event._id)
          netStarCountChange++
        }
      })
      
      // Persist changes to database
      if (eventsToStar.length > 0) {
        BrowserDB.addLabelEvent(eventsToStar, ['__ts_star']).catch(e => {
          console.error('Error starring events:', e)
        })
      }
      if (eventsToUnstar.length > 0) {
        BrowserDB.removeLabelEvent(eventsToUnstar, ['__ts_star']).catch(e => {
          console.error('Error unstarring events:', e)
        })
      }
      this.selectedEvents = []
    },
    saveSearch: function () {
      BrowserDB.createView(this.sketch.id, this.saveSearchFormName, this.currentQueryString, this.currentQueryFilter)
        .then((response) => {
          this.saveSearchFormName = ''
          this.saveSearchMenu = false
          let newView = response.data.objects[0]
          this.$store.state.meta.views.push(newView)
        })
        .catch((e) => {})
    },
    updateShowBanner: function() {
      // Show banner only when processing timelines are enabled and at
      // least one enabled timeline is in "processing" state.
      // Browser model: status is a string, not an array
      this.showBanner =
        !!this.settings.showProcessingTimelineEvents &&
        this.sketch.timelines
          .filter(tl => this.$store.state.enabledTimelines.includes(tl.id))
          .some(tl => tl.status === 'processing')
    },
    // debugEventList: function() {
    //   // Helper method to inspect eventList in browser console
    //   // Usage in console: vm.$children[X].$children[X].debugEventList()
    //   console.log('=== EventList Debug State ===')
    //   console.log('searchInProgress:', this.searchInProgress)
    //   console.log('eventList.objects.length:', this.eventList.objects.length)
    //   console.log('eventList.meta:', this.eventList.meta)
    //   console.log('currentQueryString:', this.currentQueryString)
    //   console.log('currentQueryFilter:', this.currentQueryFilter)
    //   console.log('eventList.objects sample:', this.eventList.objects.slice(0, 3))
    //   return {
    //     searchInProgress: this.searchInProgress,
    //     objectsCount: this.eventList.objects.length,
    //     meta: this.eventList.meta,
    //     objects: this.eventList.objects
    //   }
    // },
  },
  watch: {
    tableOptions: {
      handler(newVal, oldVal) {
        // Return early if the sort order changed.
        // The search is done in the sortEvents method.
        if (oldVal.sortDesc === undefined) return
        if (newVal.sortDesc[0] !== oldVal.sortDesc[0]) return

        this.paginate()
      },
      deep: true,
    },
    queryRequest: {
      handler(newQueryRequest, oldqueryRequest) {
        // Return early if this isn't a new request.
        if (newQueryRequest === oldqueryRequest || !newQueryRequest) {
          return
        }
        this.currentQueryString = newQueryRequest.queryString || ''
        this.currentQueryFilter = newQueryRequest.queryFilter || defaultQueryFilter()
        this.currentQueryDsl = newQueryRequest.queryDsl || null
        let resetPagination = newQueryRequest['resetPagination'] || false
        let incognito = newQueryRequest['incognito'] || false
        let parent = newQueryRequest['parent'] || false
        // Set additional fields. This is used when loading filter from a saved search.
        if (this.currentQueryFilter.fields) {
          this.selectedFields = this.currentQueryFilter.fields
        }
        // Preserve user defined sort order.
        if (this.sortOrderAsc) {
          this.currentQueryFilter.order = 'asc'
        } else {
          this.currentQueryFilter.order = 'desc'
        }
        this.search(resetPagination, incognito, parent)
      },
      deep: true,
    },
    'settings.showProcessingTimelineEvents': {
      handler() {
        this.updateShowBanner()
      },
    },
  },
  created() {
    console.log('[EventList.created] queryRequest:', this.queryRequest)
    console.log('[EventList.created] queryRequest.queryString:', this.queryRequest && this.queryRequest.queryString)
    
    // Check if queryRequest has actual content (not just empty observer)
    if (this.queryRequest && this.queryRequest.queryString) {
      this.currentQueryString = this.queryRequest.queryString
      this.currentQueryFilter = { ...this.queryRequest.queryFilter } || defaultQueryFilter()
      this.currentQueryDsl = { ...this.queryRequest.queryDsl }
      // Set additional fields when loading filter from a saved search.
      if (this.currentQueryFilter.fields) {
        this.selectedFields = this.currentQueryFilter.fields
      }
      const storedState = localStorage.getItem('aiSummaryCollapsed');
      if (storedState === 'true') {
        this.summaryCollapsed = true;
      }
      console.log('[EventList.created] Calling search() with queryString:', this.currentQueryString)
      this.search()
    } else {
      // No queryString provided - perform initial load with all events
      console.log('[EventList.created] No queryString in queryRequest, loading all events')
      const storedState = localStorage.getItem('aiSummaryCollapsed');
      if (storedState === 'true') {
        this.summaryCollapsed = true;
      }
      this.search()
    }
  },
}
</script>

<style lang="scss">
.ts-event-field-container {
  position: relative;
  max-width: 100%;
  padding: 0 !important;
  display: -webkit-flex;
  display: -moz-flex;
  display: flex;
  vertical-align: text-bottom !important;
}

.ts-event-field-ellipsis {
  position: absolute;
  white-space: nowrap;
  overflow-y: visible;
  overflow-x: hidden;
  text-overflow: ellipsis;
  -ms-text-overflow: ellipsis;
  -o-text-overflow: ellipsis;
  max-width: 100%;
  min-width: 0;
  width: 100%;
  top: 50%;
  transform: translateY(-50%);
  left: 0;
}

.ts-event-field-highlight {
  font-weight: bold;
  color: red;
}

.v-data-table__expanded.v-data-table__expanded__content {
  box-shadow: none !important;
}

.ts-time-bubble {
  width: 120px;
  height: 25px;
  border-radius: 20px;
  position: relative;
  margin: 0 0 0 136px;
  text-align: center;
  font-size: var(--font-size-small);
}

.ts-time-bubble-text {
  font-size: 0.8em;
  padding-top: 4px;
}

.ts-time-bubble-vertical-line {
  width: 2px;
  height: 15px;
  margin: 0 0 0 194px;
  background-color: #f5f5f5;
}

.datetime-table-cell {
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

// Adjust padding for event data table
.v-data-table td,
th {
  padding: 0 10px 0 0 !important;
}

.v-data-table td:last-child,
th:last-child {
  padding: 0 !important;
}

.v-data-table td:first-child,
th:first-child {
  padding: 0 0 0 10px !important;
}

.ts-ai-summary-card {
  border: 1px solid transparent !important;
  border-radius: 8px;
  background-color: #fafafa;
  background-image:
      linear-gradient(white, white),
      linear-gradient(90deg,
          #8ab4f8 0%,
          #81c995 20%,
          #f8c665 40%,
          #ec7764 60%,
          #b39ddb 80%,
          #8ab4f8 100%
      );
  background-origin: border-box;
  background-clip: content-box, border-box;
  background-size: 300% 100%;
  animation: borderBeamIridescent-subtle 6s linear infinite;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.08);
  display: block;
  margin-bottom: 20px;
}

.v-data-table {
  display: block; /* Ensure block display for data table */
}

@keyframes borderBeamIridescent-subtle {
    0% {
        background-position: 0% 50%;
    }
    100% {
        background-position: 100% 50%;
    }
}

.theme--dark.ts-ai-summary-card {
  background-color: #1e1e1e;
  border-color: hsla(0,0%,100%,.12) !important;
  background-image:
      linear-gradient(#1e1e1e, #1e1e1e),
      linear-gradient(90deg,
          #8ab4f8 0%,
          #81c995 20%,
          #f8c665 40%,
          #ec7764 60%,
          #b39ddb 80%,
          #8ab4f8 100%
      );
      box-shadow: 0 2px 5px rgba(255, 255, 255, 0.08);
  display: block;
  margin-bottom: 20px;
}

.ts-ai-summary-text {
  white-space: pre-line;
  word-wrap: break-word;
  overflow-wrap: anywhere;
  margin-top: -10px;
  padding-left: 10px;
  padding-right: 10px;
}

.ts-ai-summary-card .v-btn--icon {
  cursor: pointer;
}

.ts-ai-summary-card .v-btn--icon:hover {
  opacity: 0.8;
}

.ts-summary-placeholder-line {
  height: 1em;
  background-color: #e0e0e0;
  margin-bottom: 0.5em;
  border-radius: 4px;
  width: 100%;
}

.ts-summary-placeholder-line.short {
  width: 60%;
}

.ts-summary-placeholder-line.long {
  width: 80%;
}

.shimmer {
  background: linear-gradient(to right, #e0e0e0 8%, #f0f0f0 18%, #e0e0e0 33%);
  background-size: 800px 100%;
  animation: shimmer-animation 1.5s infinite linear forwards;
}

@keyframes shimmer-animation {
  0% {
    background-position: -468px 0;
  }
  100% {
    background-position: 468px 0;
  }
}

.ts-event-list-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  gap: 20px;
}

::v-deep .no-transition {
  transition: none !important;
}

.ts-ai-summary-card-title {
  display: flex;
  align-items: baseline;
}

.ts-ai-summary-title {
  margin-right: 8px;
  font-weight: normal;
}

.ts-ai-summary-subtitle {
  font-size: 0.7em;
  color: grey;
  vertical-align: middle;
  display: inline-block;
}

.actions button {
  margin-right: 10px;
}
</style>
