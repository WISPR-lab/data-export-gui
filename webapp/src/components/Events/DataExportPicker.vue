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
    <data-export-chip
      v-for="dataExport in allDataExports"
      class="mr-2 mb-3 data-export-chip"
      :key="dataExport.id + dataExport.name"
      :data-export="dataExport"
      :is-selected="isSelected(dataExport)"
      :is-empty-state="isEmptyState"
      :events-count="getCount(dataExport)"
      @remove="remove"
      @save="save"
      @toggle="toggleDataExport"
      @disableAllOtherDataExports="disableAllOtherDataExports"
    ></data-export-chip>
    <span v-if="allDataExports.length > 20">
      <v-btn text small @click="showAll = !showAll"
        >{{ showAll ? 'Show less' : 'Show all' }} ({{ project.dataExports.length }})</v-btn
      >
    </span>
  </span>
</template>

<script>
import DataExportChip from './DataExportChip.vue'
import EventBus from '../../event-bus.js'
import DB from '@/database/index.js'

import _ from 'lodash'

export default {
  components: { DataExportChip },
  props: ['currentQueryFilter', 'countPerIndex', 'countPerDataExport'],
  computed: {
    project() {
      return this.$store.state.project
    },
    allDataExports() {
      // Sort alphabetically based on data export name.
      let exports = [...this.project.dataExports]
      exports = exports.sort(function (a, b) {
        return a.name.localeCompare(b.name)
      })
      if (!this.showAll) {
        exports = exports.slice(0, 20)
      }
      return exports
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
        console.error('[DataExportPicker] Failed to delete upload:', e)
      } finally {
        this.isLoading = false
      }
    },
    async save(dataExport, dataExportName = false) {
      // Only show the progress bar if renaming the data export
      if (dataExportName) {
        this.isLoading = true
      }
      
      try {
        await DB.updateUpload(dataExport.id, {
          given_name: dataExport.name,
          color: dataExport.color
        })
        await this.$store.dispatch('updateProject', this.project.id)
        this.syncSelectedDataExports()
      } catch (e) {
        console.error('[DataExportPicker] Failed to update upload:', e)
      } finally {
        if (dataExportName) {
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
        EventBus.$emit('demo:action', 'data-export-toggled')
      }
    },
    toggleTheme() {
      this.isDarkTheme = !this.isDarkTheme
    },
    syncSelectedDataExports() {
      if (!this.currentQueryFilter || !this.currentQueryFilter.uploadIds) {
        return
      }
      const dataExports = this.project.dataExports || []
      if (this.currentQueryFilter.uploadIds.includes('_all')) {
        this.updateEnabledDataExportsIfChanged(dataExports.map((de) => de.id))
        return
      }
      let newArray = []
      this.currentQueryFilter.uploadIds.forEach((uploadId) => {
        // In browser version, uploadIds are data export IDs (strings or numbers)
        let dataExport = dataExports.find((de) => {
          return String(de.id) === String(uploadId)
        })
        if (dataExport) {
          newArray.push(dataExport)
        }
      })
      this.updateEnabledDataExportsIfChanged(newArray.map((de) => de.id))
    },
    updateEnabledDataExportsIfChanged(newDataExportIds) {
      if (!_.isEqual(newDataExportIds, this.$store.state.enabledDataExports)) {
        this.$store.dispatch('updateEnabledDataExports', newDataExportIds)
      }
    },
  },
  created() {
    EventBus.$on('isDarkTheme', this.toggleTheme)
  },
  watch: {
    'currentQueryFilter.uploadIds': {
      handler(val) {
        this.syncSelectedDataExports()
      },
      deep: true,
    },
  },
}
</script>

<!-- CSS scoped to this component only -->
<style scoped lang="scss">
.data-export-chip {
  display: inline-block;
}
</style>
