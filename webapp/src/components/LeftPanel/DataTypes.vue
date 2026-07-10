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
  <div
    v-if="iconOnly"
    class="pa-4"
    style="cursor: pointer"
    @click="
      $emit('toggleDrawer')
      expanded = true
    "
  >
    <v-icon left>mdi-database-outline</v-icon>
    <div style="height: 1px"></div>
  </div>
  <div v-else id="tsLeftPanelEventTypes">
    <div
      :style="eventTypes && eventTypes.length ? 'cursor: pointer' : ''"
      class="pa-4"
      id="tsLeftPanelEventTypesHeader"
      @click="toggleExpand"
      :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'"
    >
      <!-- <span> <v-icon left>mdi-database-outline</v-icon> Data Types </span> -->
       <span> <v-icon left>mdi-filter-multiple-outline</v-icon>Event Types</span>
      <span class="float-right" style="margin-right: 10px">
        <!-- <small v-if="eventActions"
          ><strong>{{ eventActions.length }}</strong></small
         > -->
        <small v-if="eventTypes"
          ><strong>{{ eventTypes.length }}</strong></small
        >
      </span>
    </div>

    <v-expand-transition>
      <div v-show="expanded && eventTypes.length" class="pl-8 pr-4 pb-4">
        <ts-data-types-list></ts-data-types-list>
      </div>
    </v-expand-transition>
    <v-divider></v-divider>
  </div>
</template>

<script>
import TsDataTypesList from './DataTypesList.vue'
import DB from '@/database/index.js'
import EventBus from '@/event-bus.js'

export default {
  props: {
    iconOnly: Boolean,
  },
  components: {
    TsDataTypesList,
  },
  data: function () {
    return {
      expanded: false,
      // eventActions: [],
      eventTypes: [],
    }
  },
  computed: {
    project() {
      return this.$store.state.project
    },
  },
  watch: {
    project: {
      async handler() {
        await this.loadEventTypes()
      },
      deep: true
    }
  },
  methods: {
    async loadEventTypes() {
      try {
        this.eventTypes = await DB.getEventTypes();
      } catch (e) {
        console.error('Error loading event types:', e)
        this.eventTypes = []
      }
    },
    toggleExpand() {
      if (this.eventTypes && this.eventTypes.length) {
        this.expanded = !this.expanded
        if (this.expanded && this.$store.state.demoMode) {
          EventBus.$emit('demo:action', 'event-types-expanded')
        }
      }
    },
    handleCollapse() {
      this.expanded = false
    },
    handleExpand() {
      this.expanded = true
    }
  },
  async mounted() {
    await this.loadEventTypes()

    EventBus.$on('demo:collapse-event-types', this.handleCollapse)
    EventBus.$on('demo:expand-event-types', this.handleExpand)
  },
  beforeDestroy() {
    EventBus.$off('demo:collapse-event-types', this.handleCollapse)
    EventBus.$off('demo:expand-event-types', this.handleExpand)
  }
}
</script>

<style scoped lang="scss"></style>
