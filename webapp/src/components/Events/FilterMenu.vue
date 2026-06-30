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
  <v-card width="480" style="overflow: visible">
    <v-tabs v-model="tab" grow height="34" class="filter-tabs">
      <v-tab>Absolute</v-tab>
      <v-tab>Relative</v-tab>
    </v-tabs>

     <v-container class="px-5 pt-3 pb-2">
      <v-tabs-items v-model="tab">

        <!-- ABSOLUTE TAB -->
        <v-tab-item>
          <v-select
            v-model="selectedTimezone"
            :items="timezones"
            label="Timezone"
            outlined
            dense
            hide-details
            class="mb-3 mt-1"
          ></v-select>

          <v-row dense class="mb-1">
            <!-- FROM field -->
            <v-col cols="6">
              <v-text-field
                :value="formatStartTime"
                label="From"
                outlined
                dense
                hide-details
                placeholder="Pick start"
                readonly
                :class="{ 'field-active': activePicker === 'start' }"
                :append-icon="range.start ? 'mdi-close' : ''"
                @click:append.stop="clearStart"
                @click="togglePicker('start')"
              ></v-text-field>
            </v-col>

            <!-- TO field -->
            <v-col cols="6">
              <v-text-field
                :value="formatEndTime"
                label="To (optional)"
                outlined
                dense
                hide-details
                placeholder="Pick end"
                readonly
                :class="{ 'field-active': activePicker === 'end' }"
                :append-icon="range.end ? 'mdi-close' : ''"
                @click:append.stop="clearEnd"
                @click="togglePicker('end')"
              ></v-text-field>
            </v-col>
          </v-row>

          <div class="caption grey--text mb-2" style="min-height:16px">
            <span v-if="activePicker === 'start' || activePicker === 'end'">Pick date &amp; time, then add filter below</span>
          </div>

          <!-- START picker -->
          <div v-if="activePicker === 'start'" class="picker-wrap">
            <date-picker
              :value="startDateObj"
              mode="dateTime"
              :timezone="selectedTimezone"
              :is-dark="$vuetify.theme.dark"
              is12hr
              is-expanded
              @input="onStartInput"
            ></date-picker>
          </div>

          <!-- END picker -->
          <div v-if="activePicker === 'end'" class="picker-wrap">
            <date-picker
              :value="endDateObj"
              mode="dateTime"
              :timezone="selectedTimezone"
              :is-dark="$vuetify.theme.dark"
              is12hr
              is-expanded
              :min-date="range.start ? new Date(range.start) : undefined"
              @input="onEndInput"
            ></date-picker>
          </div>
 
          <v-card-actions class="px-0 pt-2">
            <v-spacer></v-spacer>
            <v-btn small text @click="clearAndCancel">Cancel</v-btn>
            <v-btn small text color="primary" :disabled="!range.start" @click="submit">
              Add filter
            </v-btn>
          </v-card-actions>
        </v-tab-item>

        <!-- ── RELATIVE TAB ─────────────────────────────── -->
        <v-tab-item>
          <div class="relative-presets mb-4">
            <v-btn
              v-for="preset in presets"
              :key="preset.label"
              small
              depressed
              class="preset-btn mr-2 mb-2"
              @click="applyPreset(preset)"
            >{{ preset.label }}</v-btn>
          </div>

          <v-divider class="mb-4"></v-divider>

          <div class="relative-custom">
            <span class="caption grey--text mb-2 d-block">Custom range</span>
            <v-row dense align="center">
              <v-col cols="4">
                <v-text-field
                  v-model.number="customNum"
                  type="number"
                  min="1"
                  label="Amount"
                  outlined
                  dense
                  hide-details
                ></v-text-field>
              </v-col>
              <v-col cols="5">
                <v-select
                  v-model="customUnit"
                  :items="units"
                  label="Unit"
                  outlined
                  dense
                  hide-details
                ></v-select>
              </v-col>
              <v-col cols="3">
                <span class="body-2">ago</span>
              </v-col>
            </v-row>
          </div>

          <v-card-actions class="px-0 pt-3">
            <v-spacer></v-spacer>
            <v-btn small text @click="clearAndCancel">Cancel</v-btn>
            <v-btn small text color="primary" @click="applyCustomRelative">Add filter</v-btn>
          </v-card-actions>

        </v-tab-item>
 
      </v-tabs-items>
    </v-container>
  </v-card>
</template>
 
<script>
import dayjs from '@/plugins/dayjs'
import DatePicker from 'v-calendar/lib/components/date-picker.umd'

export default {
  props: ['selectedChip'],
  components: {
    DatePicker,
  },
  data() {
    return {
      tab: 0,
      activePicker: null,
      range: {
        start: '',
        end: '',
      },

      startDateObj: null,
      endDateObj: null,

      selectedTimezone: '',
      timezones: [],
      
      customNum: 1,
      customUnit: 'days',
      units: [
        { text: 'Hours',   value: 'hours'   },
        { text: 'Days',    value: 'days'    },
        { text: 'Weeks',   value: 'weeks'   },
        { text: 'Months',  value: 'months'  },
        { text: 'Years',   value: 'years'   },
      ],
      presets: [
        { label: 'Today',        num: 0,  unit: 'days'    },
        { label: 'Last 7 days',  num: 7,  unit: 'days'    },
        { label: 'Last 30 days', num: 30, unit: 'days'    },
        { label: 'Last 90 days', num: 90, unit: 'days'    },
        { label: 'Last 1 year',  num: 1,  unit: 'years'   },
      ],
    }
  },
  computed: {
    formatStartTime() {
      if (!this.range.start) return ''
      return dayjs(this.range.start).tz(this.selectedTimezone).format('MMM DD YYYY h:mm A')
    },
    formatEndTime() {
      if (!this.range.end) return ''
      return dayjs(this.range.end).tz(this.selectedTimezone).format('MMM DD YYYY h:mm A')
    },
  },
  created() {
    // Get list of all available timezones
    if (typeof Intl !== 'undefined' && Intl.supportedValuesOf) {
      try {
        this.timezones = Intl.supportedValuesOf('timeZone')
      } catch (e) {
        this.timezones = ['UTC']
      }
    } else {
      this.timezones = ['UTC']
    }
    
    // Set default to user's timezone
    const userTz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
    this.selectedTimezone = userTz
    
    if (this.selectedChip) {
      const parts = this.selectedChip.value.split(',')
      this.range.start = parts[0]
      this.range.end   = parts[1]
      this.startDateObj = this.range.start ? new Date(this.range.start) : null
      this.endDateObj   = this.range.end   ? new Date(this.range.end)   : null
    }
  },
  methods: {
    togglePicker(which) {
      if (this.activePicker === which) {
        this.activePicker = null
        return
      }
      // When opening a picker, seed it with the currently confirmed value (or now)
      if (which === 'start') {
        this.startDateObj = this.range.start ? new Date(this.range.start) : new Date()
      } else {
        this.endDateObj = this.range.end ? new Date(this.range.end) : (this.range.start ? new Date(this.range.start) : new Date())
      }
      this.activePicker = which
    },

    onStartInput(date) {
      if (!date) return
      this.startDateObj = date
      this.range.start = dayjs(date).utc().millisecond(0).toISOString()
    },
    onEndInput(date) {
      if (!date) return
      this.endDateObj = date
      this.range.end = dayjs(date).utc().millisecond(0).toISOString()
    },
 
    clearStart() {
      this.range.start = ''
      this.startDateObj = null
      this.activePicker = null
    },
    clearEnd() {
      this.range.end = ''
      this.endDateObj = null
      this.activePicker = null
    },
    clearAndCancel() {
      this.range = { start: '', end: '' }
      this.startDateObj = null
      this.endDateObj = null
      this.activePicker = null
      this.$emit('cancel')
    },
    
    
    addChip(newChip) {
      if (this.selectedChip) {
        this.$emit('updateChip', newChip)
      } else {
        this.$emit('addChip', newChip)
      }
    },
    submit: function () {
      if (!this.range.start) {
        return
      }

      this.addChip({
        field: '', type: 'datetime_range',
        value: `${this.range.start},${this.range.end}`,
        operator: 'must', active: true,
      })
      this.clearAndCancel()
      this.$emit('cancel')
  },
  applyPreset(preset) {
      const now  = dayjs().utc()
      const then = preset.num === 0 ? now.startOf('day') : now.subtract(preset.num, preset.unit)
      this.addChip({ field: '', type: 'datetime_range', value: `${then.toISOString()},${now.toISOString()}`, operator: 'must', active: true })
      this.$emit('cancel')
    },
    applyCustomRelative() {
      if (!this.customNum || this.customNum < 1) return
      const now  = dayjs().utc()
      const then = now.subtract(this.customNum, this.customUnit)
      this.addChip({ field: '', type: 'datetime_range', value: `${then.toISOString()},${now.toISOString()}`, operator: 'must', active: true })
      this.$emit('cancel')
    },
  },
}
</script>

<style scoped lang="scss">
.filter-tabs {
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
}
 
.field-active {
  ::v-deep .v-input__slot {
    border-color: var(--v-primary-base) !important;
    box-shadow: 0 0 0 1px var(--v-primary-base);
  }
}
 
.picker-wrap {
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  padding-top: 8px;
}
 
.preset-btn {
  font-size: 12px;
  text-transform: none;
  letter-spacing: 0;
}
 
.relative-custom .caption {
  font-size: 11px;
}



</style>
