<!-- modified for anonymous-research-group/data-export-gui -->
<template>
  <v-dialog v-model="dialogVisible" max-width="1200px" scrollable>
    <v-card v-if="events && events.length >= 2">
      <!-- Simple Header -->
      <v-card-title class="d-flex justify-space-between align-center py-2 px-4">
        <span class="text-h6 font-weight-medium">Event Comparison</span>
        <v-btn icon small @click="closeDialog">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider></v-divider>

      <!-- Table Body -->
      <v-card-text class="pa-0">
        <v-simple-table dense>
          <template v-slot:default>
            <thead>
              <tr>
                <th
                  class="text-left font-weight-medium text-body-2 text--primary py-2"
                  style="width: 200px; background-color: rgba(0, 0, 0, 0.03);"
                >
                  Attribute
                </th>
                <th
                  v-for="(ev, idx) in events"
                  :key="ev._id || idx"
                  class="text-left py-2 align-middle"
                  style="background-color: rgba(0, 0, 0, 0.03);"
                >
                  <!-- Label + Inline Star & Tag Menu -->
                  <div class="d-flex align-center" style="gap: 4px;">
                    <span class="text-body-2 font-weight-medium text--primary">{{ getEventLabel(ev) }}</span>
                    
                    <!-- Star button matching EventList.vue -->
                    <v-btn small icon @click="toggleStar(ev)" class="ml-1">
                      <v-icon title="Toggle star status" v-if="ev._source && ev._source.starred === 1" color="amber">
                        mdi-star
                      </v-icon>
                      <v-icon title="Toggle star status" v-else>
                        mdi-star-outline
                      </v-icon>
                    </v-btn>

                    <!-- Tag menu matching EventList.vue -->
                    <ts-event-tag-menu :event="ev"></ts-event-tag-menu>
                  </div>

                  <!-- Display active tags -->
                  <div v-if="getEventTags(ev).length" class="d-flex flex-wrap mt-1" style="gap: 4px;">
                    <v-chip
                      v-for="tag in getEventTags(ev)"
                      :key="tag"
                      x-small
                      class="px-1"
                      style="height: 18px; font-size: 0.7rem;"
                    >
                      {{ tag }}
                    </v-chip>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in tableRows"
                :key="row.key"
                :class="{ 'diff-row': row.isDifferent }"
              >
                <!-- Key -->
                <td class="font-weight-medium text-body-2 py-2 align-top text--primary">
                  {{ row.key }}
                </td>

                <!-- Values for each event -->
                <td
                  v-for="(val, idx) in row.values"
                  :key="idx"
                  class="text-body-2 py-2 align-top text--primary"
                >
                  <template v-if="val !== undefined && val !== null">
                    {{ val }}
                  </template>
                </td>
              </tr>
            </tbody>
          </template>
        </v-simple-table>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script>
import DB from '@/database/index.js'
import TsEventTagMenu from './EventTagMenu.vue'
import { FIELDS_EXCLUDED_FROM_ATTRIBUTE_TABLE } from '@/constants/app_constants.js'

export default {
  name: 'CompareEventsDialog',
  components: {
    TsEventTagMenu,
  },
  computed: {
    dialogVisible: {
      get() {
        return this.$store.state.showCompareDialog
      },
      set(val) {
        this.$store.commit('SET_SHOW_COMPARE_DIALOG', val)
      },
    },
    events() {
      return this.$store.state.compareEvents || []
    },
    tableRows() {
      if (!this.events || this.events.length < 2) return []

      const keySet = new Set()
      const eventFilteredSources = this.events.map((ev) => {
        const source = (ev && ev._source) || {}
        const filtered = Object.keys(source)
          .filter((key) => !FIELDS_EXCLUDED_FROM_ATTRIBUTE_TABLE.includes(key) && !key.startsWith('__ts') && !key.startsWith('norm__') && source[key] !== '')
          .reduce((obj, key) => {
            obj[key] = source[key]
            return obj
          }, {})
        Object.keys(filtered).forEach((k) => keySet.add(k))
        return filtered
      })

      const allKeys = Array.from(keySet).sort()

      return allKeys.map((key) => {
        const values = eventFilteredSources.map((source) => source[key])

        // Only compare valid non-null / non-undefined / non-empty values
        const validValues = values.filter((v) => v !== undefined && v !== null && v !== '')
        let isDifferent = false

        if (validValues.length >= 2) {
          const firstStr = JSON.stringify(validValues[0])
          for (let i = 1; i < validValues.length; i++) {
            if (JSON.stringify(validValues[i]) !== firstStr) {
              isDifferent = true
              break
            }
          }
        }

        return {
          key,
          values,
          isDifferent,
        }
      })
    },
  },
  methods: {
    closeDialog() {
      this.$store.commit('SET_SHOW_COMPARE_DIALOG', false)
    },
    getEventLabel(ev) {
      if (!ev || !ev._source) return ''
      const ts = ev._source.primary_timestamp || ev._source.datetime || ''
      let formattedTs = ts
      if (ts && this.$options.filters && this.$options.filters.shortDateTimeLocal) {
        formattedTs = this.$options.filters.shortDateTimeLocal(ts)
      }
      const name = ev._source.data_export_name || ev._source.filename || ''
      return name ? `${formattedTs} (${name})` : formattedTs
    },
    getEventTags(ev) {
      if (!ev || !ev._source || !Array.isArray(ev._source.tag)) return []
      return ev._source.tag.filter((t) => t && t !== 'starred')
    },
    toggleStar(ev) {
      if (!ev || !ev._source) return
      if (!ev._source.labels) ev._source.labels = []
      const isStarred = ev._source.starred === 1
      if (isStarred) {
        ev._source.starred = 0
        const idx = ev._source.labels.indexOf('starred')
        if (idx > -1) ev._source.labels.splice(idx, 1)
        this.$store.dispatch('updateEventLabels', { label: 'starred', num: -1 })
        DB.removeLabelEvent(this.$route.meta.dbName || 'userdata', [ev._id], ['starred']).catch((e) => console.error(e))
      } else {
        ev._source.starred = 1
        ev._source.labels.push('starred')
        this.$store.dispatch('updateEventLabels', { label: 'starred', num: 1 })
        DB.addLabelEvent(this.$route.meta.dbName || 'userdata', [ev._id], ['starred']).catch((e) => console.error(e))
      }
    },
  },
}
</script>

<style scoped lang="scss">
.diff-row {
  background-color: rgba(255, 236, 179, 0.4);
}

.v-application--is-dark .diff-row {
  background-color: rgba(255, 179, 0, 0.15);
}
</style>
