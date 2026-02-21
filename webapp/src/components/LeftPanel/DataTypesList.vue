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
  <div>
    <v-data-iterator
      :items="eventActions"
      :items-per-page.sync="itemsPerPage"
      :search="search"
      :hide-default-footer="eventActions.length <= itemsPerPage"
    >
      <template v-slot:header v-if="eventActions.length > itemsPerPage">
        <v-toolbar flat>
          <v-text-field
            v-model="search"
            clearable
            hide-details
            outlined
            dense
            prepend-inner-icon="mdi-magnify"
            label="Search for a category.."
          ></v-text-field>
        </v-toolbar>
      </template>

      <template v-slot:default="props">
        <!-- <div
          v-for="dataType in props.items"
          :key="dataType.data_type"
          @click="setQueryAndFilter(dataType.data_type)"
          style="cursor: pointer; font-size: 0.9em"
        > -->
        <div
          v-for="action in props.items"
          :key="action.action"
          @click="setQueryAndFilter(action.action)"
          style="cursor: pointer; font-size: 0.9em"
        >
          <v-row no-gutters class="pa-2 pl-5" :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'">
            <span
              >{{ action.action }} (<small
                ><strong>{{ action.count | compactNumber }}</strong></small
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

export default {
  props: [],
  data: function () {
    return {
      itemsPerPage: 10,
      search: '',
    }
  },
  computed: {
    eventActions() {
      return [...(this.$parent.eventActions || [])].sort((a, b) => a.action.localeCompare(b.action))
    },
  },
  methods: {
    setQueryAndFilter(action) {
      let eventData = {}
      eventData.doSearch = true
      eventData.queryString = 'event_action:' + '"' + action + '"'
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
