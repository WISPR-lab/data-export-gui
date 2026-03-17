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
  <v-card :outlined="!flat" :class="{ 'ma-4': !flat }">
    <!-- Header Section -->
    <slot name="header"></slot>

    <!-- Scrollable Content Section -->
    <v-card-text>
      <v-row no-gutters>
        <v-col style="min-width: 250px; flex-basis: 25%">
          <div class="pa-2">
            <v-simple-table>
              <template v-slot:default>
                <thead>
                  <tr>
                    <th class="text-left">Description</th>
                    <th class="text-left">Example Query</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Search all events</td>
                    <td>
                      <a href="#" @click.prevent="emitSetQueryAndFilter('*')">
                        <code>*</code>
                      </a>
                    </td>
                  </tr>
                  <tr>
                    <td>Search a word in message field</td>
                    <td>
                      <a href="#" @click.prevent="emitSetQueryAndFilter('message:log')">
                        <code>message:log</code>
                      </a>
                    </td>
                  </tr>
                  <tr>
                    <td>Search an exact phrase</td>
                    <td>
                      <a href="#" @click.prevent="emitSetQueryAndFilter('&quot;Successful login&quot;')">
                        <code>"Successful login"</code>
                      </a>
                    </td>
                  </tr>
                  <tr>
                    <td>Wildcard search (prefix/suffix)</td>
                    <td>
                      <a href="#" @click.prevent="emitSetQueryAndFilter('event_action:password*')">
                        <code>event_action:password*</code>
                      </a>
                    </td>
                  </tr>
                  <tr>
                    <td>Multiple terms (implicit AND)</td>
                    <td>
                      <a href="#" @click.prevent="emitSetQueryAndFilter('log out')">
                        <code>log out</code>
                      </a>
                    </td>
                  </tr>
                  <tr>
                    <td>Boolean OR search</td>
                    <td>
                      <a href="#" @click.prevent="emitSetQueryAndFilter('message:login OR message:logout')">
                        <code>message:login OR message:logout</code>
                      </a>
                    </td>
                  </tr>
                  <tr>
                    <td>Boolean NOT search</td>
                    <td>
                      <a href="#" @click.prevent="emitSetQueryAndFilter('message:login NOT message:attempt')">
                        <code>message:login NOT message:attempt</code>
                      </a>
                      <br/>
                      <a href="#" @click.prevent="emitSetQueryAndFilter('login -attempt')">
                        <code>login -attempt</code>
                      </a>
                    </td>
                  </tr>
                  <tr>
                    <td>Grouped search with parentheses</td>
                    <td>
                      <a href="#" @click.prevent="emitSetQueryAndFilter('(reset OR changed) AND message:password*')">
                        <code>(reset OR changed) AND message:password*</code>
                      </a>
                    </td>
                  </tr>
                  <tr>
                    <td>Search across default fields <br/><span class="caption">(message, attributes, event_action, category, event_kind, platform)</span></td>
                    <td>
                      <a href="#" @click.prevent="emitSetQueryAndFilter('success')">
                        <code>success</code>
                      </a>
                    </td>
                  </tr>
                </tbody>
              </template>
            </v-simple-table>
          </div>
        </v-col>

        <!-- Dynamically load Tags, DataTypes and SavedSearches Lists -->
        <v-col v-if="showTags" style="border-left: 1px solid rgba(0, 0, 0, 0.12)">
          <div class="pa-4">
            <h5><v-icon left>mdi-tag-multiple-outline</v-icon> Tags</h5>
            <ts-tags-list></ts-tags-list>
          </div>
        </v-col>
        <v-col v-if="false && showDataTypes" style="border-left: 1px solid rgba(0, 0, 0, 0.12)">
          <div class="pa-4">
            <h5><v-icon left>mdi-database-outline</v-icon> Data Types</h5>
            <ts-data-types-list></ts-data-types-list>
          </div>
        </v-col>
        <v-col v-if="showSavedSearches" style="border-left: 1px solid rgba(0, 0, 0, 0.12)">
          <div class="pa-4">
            <h5><v-icon left>mdi-content-save-outline</v-icon> Saved Searches</h5>
            <ts-saved-searches-list></ts-saved-searches-list>
          </div>
        </v-col>
      </v-row>
    </v-card-text>

    <!-- Actions Section -->
    <v-divider></v-divider>
    <v-card-actions>
      <!-- Link removed: rules now documented in local examples -->
    </v-card-actions>
  </v-card>
</template>

<script>
import EventBus from '../../event-bus.js'

import TsTagsList from '../LeftPanel/TagsList.vue'
import TsDataTypesList from '../LeftPanel/DataTypesList.vue'
import TsSavedSearchesList from '../LeftPanel/SavedSearchesList.vue'

export default {
  name: 'TsSearchGuideCard',
  props: {
    flat: {
      type: Boolean,
      default: false,
    },
    showTags: {
      type: Boolean,
      default: false,
    },
    showDataTypes: {
      type: Boolean,
      default: false,
    },
    showSavedSearches: {
      type: Boolean,
      default: false,
    },
  },
  components: {
    TsTagsList,
    TsDataTypesList,
    TsSavedSearchesList,
  },
  computed: {
    firstOfCurrentMonth() {
      const now = new Date()
      const year = now.getFullYear()
      const month = String(now.getMonth() + 1).padStart(2, '0')
      return `${year}-${month}-01`
    },
    nowDateTimeUTC() {
      const now = new Date()
      return now.toISOString().slice(0, 19)
    },
  },
  methods: {
    emitSetQueryAndFilter(queryString) {
      let eventData = {}
      eventData.doSearch = true
      eventData.queryString = queryString
      EventBus.$emit('setQueryAndFilter', eventData)
      this.$emit('search-triggered')
    },
  },
}
</script>

<style scoped></style>
