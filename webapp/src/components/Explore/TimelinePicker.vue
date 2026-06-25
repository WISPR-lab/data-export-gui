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
<!-- modified for WISPR-lab/data-export-gui -->
<template>
  <span>
    <ts-timeline-chip
      v-for="timeline in allDataExports"
      class="mr-2 mb-3 timeline-chip"
      :key="dataExport.id + dataExport.name"
      :data-export="timeline"
      :is-selected="isSelected(timeline)"
      :is-empty-state="isEmptyState"
      :events-count="getCount(timeline)"
      @remove="remove"
      @save="save"
      @toggle="toggleDataExport"
      @disableAllOtherDataExports="disableAllOtherDataExports"
    ></ts-timeline-chip>
    <span v-if="allDataExports.length > 20">
      <v-btn text small @click="showAll = !showAll"
        >{{ showAll ? 'Show less' : 'Show all' }} ({{ project.dataExports.length }})</v-btn
      >
    </span>
  </span>
</template>

<script>
import TsTimelineChip from './TimelineChip.vue'
import EventBus from '../../event-bus.js'
import DB from '@/database/index.js'

import _ from 'lodash'

export default {
  components: { TsTimelineChip },
  props: ['currentQueryFilter', 'countPerIndex', 'countPerDataExport'],
  computed: {
    project() {
      return this.$store.state.project
    },
    allDataExports() {
      // Sort alphabetically based on timeline name.
      let timelines = [...this.project.dataExports]
      timelines = timelines.sort(function (a, b) {
        return a.name.localeCompare(b.name)
      })
      if (!this.showAll) {
        timelines = timelines.slice(0, 20)
      }
      return timelines
    },
    activeDataExports() {
      // Sort alphabetically based on timeline name.
      let timelines = [...this.project.dataExports]
      return timelines.sort(function (a, b) {
        return a.name.localeCompare(b.name)
      })
    },
    isEmptyState() {
      return this.countPerDataExport === undefined
    },
  },
  data() {
    return {
      isDarkTheme: false,
      isLoading: false,
      showAll: false,
    }
  },
  methods: {
    isSelected(dataExport) {
      return this.$store.state.enabledDataExports.includes(dataExport.id)
    },
    getCount(dataExport) {
      if (this.countPerDataExport) {
        const count = this.countPerDataExport[dataExport.id]
        if (typeof count === 'number') {
          return count
        }
      }
      return 0
    },
    async remove(dataExport) {
      this.isLoading = true
      try {
        await DB.deleteUpload(dataExport.id)
        await this.$store.dispatch('updateProject', this.project.id)
        this.syncSelectedDataExports()
      } catch (e) {
        console.error('[TimelinePicker] Failed to delete upload:', e)
      } finally {
        this.isLoading = false
      }
    },
    async save(dataExport, newTimelineName = false) {
      // Only show the progress bar if renaming the timeline
      if (newTimelineName) {
        this.isLoading = true
      }
      
      try {
        await DB.updateUpload(dataExport.id, {
          given_name: newTimelineName || dataExport.name,
          color: dataExport.color
        })
        await this.$store.dispatch('updateProject', this.project.id)
        this.syncSelectedDataExports()
      } catch (e) {
        console.error('[TimelinePicker] Failed to update upload:', e)
      } finally {
        if (newTimelineName) {
          this.isLoading = false
        }
      }
    },
    disableAllOtherDataExports(dataExport) {
      this.$store.dispatch('updateEnabledDataExports', [dataExport.id])
    },
    toggleDataExport(dataExport) {
      this.$store.dispatch('toggleEnabledDataExport', dataExport.id)
      if (this.$store.state.demoMode) {
        EventBus.$emit('demo:action', 'timeline-toggled')
      }
    },
    toggleTheme() {
      this.isDarkTheme = !this.isDarkTheme
    },
    syncSelectedDataExports() {
      if (!this.currentQueryFilter || !this.currentQueryFilter.uploadIds) {
        return
      }
      if (this.currentQueryFilter.uploadIds.includes('_all')) {
        this.updateEnabledDataExportsIfChanged(this.activeDataExports.map((tl) => tl.id))
        return
      }
      let newArray = []
      this.currentQueryFilter.uploadIds.forEach((uploadId) => {
        // In browser version, uploadIds are timeline IDs (strings or numbers)
        let timeline = this.activeDataExports.find((t) => {
          return String(t.id) === String(uploadId)
        })
        if (timeline) {
          newArray.push(timeline)
        }
      })
      this.updateEnabledDataExportsIfChanged(newArray.map((tl) => tl.id))
    },
    updateEnabledDataExportsIfChanged(newTimelineIds) {
      if (!_.isEqual(newTimelineIds, this.$store.state.enabledDataExports)) {
        this.$store.dispatch('updateEnabledDataExports', newTimelineIds)
      }
    },
  },
  created() {
    EventBus.$on('isDarkTheme', this.toggleTheme)
  },
  watch: {
    'currentQueryFilter.uploadIds'(val) {
      this.syncSelectedDataExports()
    },
    deep: true,
  },
}
</script>

<!-- CSS scoped to this component only -->
<style scoped lang="scss">
.timeline-chip {
  display: inline-block;
}
</style>
