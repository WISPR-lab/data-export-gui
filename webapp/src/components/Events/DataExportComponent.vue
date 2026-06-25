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
<!-- modified for WISPR-lab/data-export-gui -->
<!--
  A generic export component that provides common export related
  functionality and allows customization of the template. That way a export
  can be represented as a chip or a table row.
-->

<template>
  <span v-if="dataExport && dataExport.id">

    <v-menu
      offset-y
      max-width="385"
      :close-on-content-click="false"
      content-class="menu-with-gap"
      ref="dataExportChipMenuRef"
      @input="onMenuToggle"
    >
      <template v-slot:activator="{ on }">
        <slot
          name="processed"
          :dataExportFailed="dataExportFailed"
          :dataExportChipColor="dataExportChipColor"
          :dataExportStatus="dataExport.status"
          :events="{
            toggleDataExport,
            openDialog,
            menuOn: on,
          }"
        ></slot>
      </template>
      <v-sheet flat>
        <v-list dense>
          <v-dialog v-model="dialogRename" width="600">
            <template v-slot:activator="{ on, attrs }">
              <v-list-item v-bind="attrs" v-on="on">
                <v-list-item-action>
                  <v-icon>mdi-square-edit-outline</v-icon>
                </v-list-item-action>
                <v-list-item-subtitle>Rename</v-list-item-subtitle>
              </v-list-item>
            </template>
            <v-card class="pa-4">
              <v-form @submit.prevent="rename()">
                <h3>Rename data export</h3>
                <br />
                <v-text-field clearable outlined dense autofocus v-model="dataExportName" @focus="$event.target.select()" :rules="dataExportNameRules">
                </v-text-field>
                <v-card-actions>
                  <v-spacer></v-spacer>
                  <v-btn text @click="dialogRename = false"> Cancel </v-btn>
                  <v-btn :disabled="!dataExportName || dataExportName.length > 255" color="primary" text @click="rename()"> Save </v-btn>
                </v-card-actions>
              </v-form>
            </v-card>
          </v-dialog>

          <v-list-item id="exportVisibilityToggle" v-if="dataExportAvailable" @click="$emit('toggle', dataExport)">
            <v-list-item-action>
              <v-icon v-if="isSelected">mdi-eye-off</v-icon>
              <v-icon v-else>mdi-eye</v-icon>
            </v-list-item-action>
            <v-list-item-subtitle v-if="isSelected">Temporarily disabled</v-list-item-subtitle>
            <v-list-item-subtitle v-else>Re-enable</v-list-item-subtitle>
          </v-list-item>

          <v-list-item v-if="dataExportAvailable" @click="$emit('disableAllOtherDataExports', dataExport)">
            <v-list-item-action>
              <v-icon>mdi-checkbox-marked-circle-minus-outline</v-icon>
            </v-list-item-action>
            <v-list-item-subtitle>Unselect other data exports</v-list-item-subtitle>
          </v-list-item>

          <v-dialog v-model="dialogStatus" width="800">
            <template v-slot:activator="{ on, attrs }">
              <v-list-item v-bind="attrs" v-on="on">
                <v-list-item-action>
                  <v-icon :color="iconStatus === 'mdi-alert-circle-outline' ? 'red' : ''">{{ iconStatus }}</v-icon>
                </v-list-item-action>
                <v-list-item-subtitle>Uploaded files ({{ documentMetadata.length }})</v-list-item-subtitle>
              </v-list-item>
            </template>
            <v-card>
              <div class="pa-4">
                <ul style="list-style-type: none">
                  <li><strong>Upload name: </strong>{{ dataExport.name }}</li>
                  <li v-if="dataExport.status === 'processing' || dataExport.status === 'ready'">
                    <strong>Number of events: </strong>
                    {{ dataExport.event_count | compactNumber }}
                  </li>
                  <!-- <li><strong>Created by: </strong>{{ dataExport.user.username }}</li> -->
                  <li>
                    <strong>Created at: </strong>{{ dataExport.created_at | shortDateTime }}
                    <small>({{ dataExport.created_at | timeSince }})</small>
                  </li>
                  <li><strong>Number of files uploaded: </strong>{{ documentMetadata.length }}</li>
                  <v-spacer class="ma-5"></v-spacer>
                  <li class="font-italic">
                    This tool doesn't process all files in the ZIP you uploaded, only those that are useful for security analysis. If parsing fails for any file in the ZIP, its contents will not be indexed by the tool. To upload these files again, delete the upload and re-import the data.
                  </li>
                </ul>

                <!-- <v-alert text class="ma-5">
                  This tool doesn't process all files in the ZIP you uploaded, only those that are useful for security analysis. If parsing fails for any file in the ZIP, its contents will not be indexed by the tool. To upload these files again, delete the upload and re-import the data.
                </v-alert> -->

                <v-alert
                  v-for="doc in documentMetadata"
                  :key="doc.id"
                  border="top"
                  colored-border
                  text
                  dense
                  :type="doc.parse_status === 'fail' ? 'error' : 'success'"
                  class="ma-5"
                >
                  <ul style="list-style-type: none">
                    <li><strong>File name:</strong> {{ doc.manifest_filename }}</li>
                    <li><strong>File size:</strong> {{ doc.file_size_bytes | compactBytes }}</li>
                    <li v-if="doc.parse_status === 'fail'">
                      <strong>Status:</strong> <code>parse failed</code>
                    </li>
                    <!-- <li v-else class="text-success">✓ Parsed successfully</li> -->
                  </ul>
                </v-alert>
              </div>
              <v-divider></v-divider>
              <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn color="primary" text @click="dialogStatus = false"> Close </v-btn>
              </v-card-actions>
            </v-card>
          </v-dialog>


          <v-list-item v-if="dataExportAvailable" style="cursor: pointer" @click="deleteConfirmation = true">
            <v-list-item-action>
              <v-icon>mdi-trash-can-outline</v-icon>
            </v-list-item-action>
            <v-list-item-subtitle>Delete</v-list-item-subtitle>
          </v-list-item>
          <v-dialog v-model="deleteConfirmation" max-width="500">
            <v-card>
              <v-card-title>
                <v-icon color="red" class="mr-2 ml-n3">mdi-alert-octagon-outline</v-icon> Delete Data Export?
              </v-card-title>
              <v-card-text>
                <ul style="list-style-type: none">
                  <li><strong>Name: </strong>{{ dataExport.name }}</li>
                  <li><strong>Status: </strong>{{ dataExport.status }}</li>
                  <li>
                    <strong>Number of events: </strong>
                    {{ dataExport.event_count | compactNumber }}
                  </li>
                  <!-- <li><strong>Created by: </strong>{{ dataExport.user.username }}</li> -->
                  <li>
                    <strong>Created at: </strong>{{ dataExport.created_at | shortDateTime }}
                    <small>({{ dataExport.created_at | timeSince }})</small>
                  </li>
                </ul>
              </v-card-text>
              <v-card-actions>
                <v-btn color="primary" text @click="deleteConfirmation = false"> cancel </v-btn>
                <v-spacer></v-spacer>
                <v-btn color="primary" text @click="remove()"> delete </v-btn>
              </v-card-actions>
            </v-card>
          </v-dialog>
        </v-list>
        <div v-if="!dataExportFailed" class="px-4">
          <v-color-picker
            @update:color="updateColor"
            :value="'#' + dataExport.color"
            :show-swatches="!showCustomColorPicker"
            :swatches="colorPickerSwatches"
            :hide-canvas="!showCustomColorPicker"
            :hide-sliders="!showCustomColorPicker"
            hide-inputs
            mode="hexa"
            dot-size="15"
          ></v-color-picker>
          <v-btn text x-small class="mt-2" @click="showCustomColorPicker = !showCustomColorPicker">
            <span v-if="showCustomColorPicker">Palette</span>
            <span v-else>Custom color</span>
          </v-btn>
        </div>
        <br />
      </v-sheet>
    </v-menu>
  </span>
</template>

<script>
import Vue from 'vue'
import DB from '@/database/index.js'
import EventBus from '@/event-bus.js'

const gradients = [
  ['#222'],
  ['#42b3f4'],
  ['red', 'orange', 'yellow'],
  ['purple', 'violet'],
  ['#00c6ff', '#F0F', '#FF0'],
  ['#f72047', '#ffd200', '#1feaea'],
]

export default {
  props: ['dataExport', 'eventsCount', 'isSelected', 'isEmptyState'],
  data() {
    return {
      allIndexedEvents: 0, // all indexed events from ready and processed datasources
      totalEvents: null,
      dialogStatus: false,
      dialogRename: false,
      documentMetadata: [], // Browser model: uploaded files from document_metadata table
      eventsPerSecond: [],
      dataExportName: [...this.dataExport.name],
      sparkline: {
        width: 2,
        radius: 10,
        padding: 8,
        lineCap: 'round',
        gradient: gradients[5],
        gradientDirection: 'bottom',
        gradients,
        fill: false,
        type: 'trend',
        autoDrawDuration: 4000,
        autoLineWidth: false,
      },
      showCustomColorPicker: false,
      colorPickerSwatches: [
        ['#5E75C2', '#BB77C4', '#FD7EAC'],
        ['#FF9987', '#FFC66A', '#F9F871'],
        ['#FFB5BC', '#97D788', '#9BC1AF'],
        ['#FFC7A0', '#FFDF79', '#FFEAEF'],
        ['#DEBBFF', '#9AB0FB', '#CFFBE2'],
      ],
      deleteConfirmation: false,
      dataExportNameRules: [
        (v) => !!v || 'Data export name is required.',
        (v) => (v && v.length <= 255) || 'Data export name is too long.',
      ],
    }
  },
  computed: {
    meta() {
      return this.$store.state.meta
    },
    // datasourceErrors() {
    //   const datasources = this.dataExport && this.dataExport.datasources ? this.dataExport.datasources : []
    //   return datasources.filter((datasource) => datasource.error_message)
    // },
    // datasourcesProcessing() {
    //   return this.datasources.filter(
    //     (datasource) =>
    //       this.dataSourceStatus(datasource) === 'processing' || this.dataSourceStatus(datasource) === 'queueing'
    //   )
    // },
    project() {
      return this.$store.state.project
    },
    // totalEventsToIndex() {
    //   return this.datasources
    //     .filter((x) => this.dataSourceStatus(x) === 'processing')
    //     .map((x) => x.total_file_events)
    //     .reduce((a, b) => a + b, 0)
    // },
    // secondsToComplete() {
    //   return this.totalEventsToIndex / this.avarageEventsPerSecond()
    // },
    // percentComplete() {
    //   return Math.floor((this.secondsSinceStart() / this.secondsToComplete) * 100) || 0
    // },
    iconStatus() {
      if (this.dataExport.status === 'ready') return 'mdi-information-outline'
      if (this.dataExport.status === 'processing') return 'mdi-circle-slice-7'
      return 'mdi-alert-circle-outline'
    },
    dataExportFailed() {
      return this.dataExport.status === 'fail'
    },
    dataExportAvailable() {
      return (
        this.dataExport.status === 'ready' ||
        this.dataExport.status === 'fail' ||
        (this.settings.showProcessingData && this.dataExport.status === 'processing')
      )
    },
    dataExportChipColor() {
      if (!this.dataExport || !this.dataExport.color) return '#5E75C2'
      if (!this.dataExport.color.startsWith('#')) {
        return '#' + this.dataExport.color
      }
      return this.dataExport.color
    },
    settings() {
      return this.$store.state.settings
    },
  },
  methods: {
    openDialog() {
      this.dialogStatus = true
    },
    rename() {
      this.dialogRename = false
      this.$emit('save', this.dataExport, this.dataExport.name)
    },
    remove() {
      this.$emit('remove', this.dataExport)
      this.deleteConfirmation = false
      this.successSnackBar('Data export deleted')
    },
    // secondsSinceStart() {
    //   if (!this.datasourcesProcessing.length) {
    //     return 0
    //   }
    //   let start = dayjs.utc(this.datasourcesProcessing[0].updated_at)
    //   let end = dayjs.utc()
    //   let diffSeconds = end.diff(start, 'second')
    //   return diffSeconds
    // },
    // avarageEventsPerSecond() {
    //   const sum = this.eventsPerSecond.reduce((a, b) => a + b, 0)
    //   const avg = sum / this.eventsPerSecond.length || 0
    //   return Math.floor(avg)
    // },
    // processingETA() {
    //   let secondsLeft = this.secondsToComplete - this.secondsSinceStart()
    //   let eta = dayjs().add(secondsLeft, 'second').fromNow()
    //   return eta
    // },
    onMenuToggle(isOpen) {
      if (isOpen && this.$store.state.demoMode) {
        EventBus.$emit('demo:action', 'menu-opened')
      }
    },
    toggleDataExport() {
      if (!this.dataExportFailed) {
        this.$emit('toggle', this.dataExport)
      }
    },
    // Browser model: no server, so no need for debounce
    updateColor(color) {
      Vue.set(this.dataExport, 'color', color.hex.substring(1))
      this.$emit('save', this.dataExport)
    },
    async loadDocumentMetadata() {
      try {
        this.documentMetadata = await DB.getUploadedFiles(this.dataExport.id)
      } catch (e) {
        console.error('[DataExportComponent] Failed to load uploaded files:', e)
        this.documentMetadata = []
      }
    },
  },
  created() {
    if (!this.dataExport || !this.dataExport.status) {
      return
    }
    this.loadDocumentMetadata()
  },
  beforeDestroy() {
    clearInterval(this.t)
    this.t = false
  },
}
</script>

<!-- CSS scoped to this component only -->
<style scoped lang="scss">
.data-export-chip {
  .right {
    margin-left: auto;
  }

  .chip-content {
    margin: 0;
    padding: 0;
    display: flex;
    align-items: center;
    width: 300px;
  }
}

.v-chip.data-export-chip.failed {
  cursor: auto;
}

.v-chip.data-export-chip.failed:hover:before {
  opacity: 0;
}

.events-count {
  font-size: 0.8em;
}

.disabled {
  text-decoration: line-through;
}
</style>
