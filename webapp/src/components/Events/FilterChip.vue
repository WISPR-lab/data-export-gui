<template>
  <v-menu offset-y content-class="menu-with-gap">
    <template v-slot:activator="{ on: onMenu }">
      <v-tooltip top :disabled="formatChipDisplay(chip).length < 33" open-delay="300">
        <template v-slot:activator="{ on: onTooltip, attrs }">
          <v-chip
            outlined
            close
            close-icon="mdi-close"
            @click:close="$emit('remove', chip)"
            v-on="{ ...onMenu, ...onTooltip }"
            v-bind="attrs"
          >
            <!-- Icon for time chips -->
            <v-icon v-if="isTimeChip" left small>mdi-clock-outline</v-icon>

            <!-- Icons for term/tag/label chips -->
            <v-icon v-else-if="chip.value === '__ts_star'" left small color="amber">mdi-star</v-icon>
            <v-icon v-else-if="chip.value === '__ts_comment'" left small>mdi-comment-multiple-outline</v-icon>
            <v-icon v-else-if="getQuickTag(chip.value)" left small :color="getQuickTag(chip.value).color">{{
              getQuickTag(chip.value).label
            }}</v-icon>

            <!-- Text styling based on active state -->
            <span v-bind:style="[chip.active === false ? { 'text-decoration': 'line-through', opacity: '50%' } : '']">
              <span v-if="chip.operator === 'must_not'" class="filter-chip-truncate">
                <span style="color: red">NOT </span>
                {{ formatChipDisplay(chip) }}
              </span>
              <span v-else class="filter-chip-truncate">
                {{ formatChipDisplay(chip) }}
              </span>
            </span>
          </v-chip>
        </template>
        <span>{{ chip.value }}</span>
      </v-tooltip>
    </template>
    <v-card>
      <v-list dense>
        <!-- Option 1: Edit for time chips, Operator Toggle for regular chips -->
        <v-menu
          v-if="isTimeChip"
          offset-y
          :close-on-content-click="false"
          :close-on-click="true"
          nudge-top="70"
          content-class="menu-with-gap"
          allow-overflow
          style="overflow: visible"
        >
          <template v-slot:activator="{ on, attrs }">
            <v-list-item v-bind="attrs" v-on="on">
              <v-list-item-action class="mr-3">
                <v-icon>mdi-square-edit-outline</v-icon>
              </v-list-item-action>
              <v-list-item-subtitle>Edit filter</v-list-item-subtitle>
            </v-list-item>
          </template>
          <filter-menu app :selected-chip="chip" @updateChip="$emit('update', $event, chip)"></filter-menu>
        </v-menu>

        <!-- <v-list-item v-else @click="$emit('toggle-operator', chip)">
          <v-list-item-action class="mr-3">
            <v-icon>mdi-swap-horizontal</v-icon>
          </v-list-item-action>
          <v-list-item-subtitle>
            <span v-if="chip.operator === 'must_not'">Change to MUST</span>
            <span v-else>Change to NOT</span>
          </v-list-item-subtitle>
        </v-list-item> -->

        <!-- Option 2: Temporarily disable / Re-enable (Common) -->
        <v-list-item @click="$emit('toggle', chip)">
          <v-list-item-action class="mr-3">
            <v-icon v-if="chip.active !== false">mdi-eye-off</v-icon>
            <v-icon v-else>mdi-eye</v-icon>
          </v-list-item-action>
          <v-list-item-subtitle>
            <span v-if="chip.active !== false">Temporarily disable</span>
            <span v-else>Re-enable</span>
          </v-list-item-subtitle>
        </v-list-item>

        <!-- Option 3: Remove filter (Common) -->
        <v-list-item @click="$emit('remove', chip)">
          <v-list-item-action class="mr-3">
            <v-icon>mdi-delete</v-icon>
          </v-list-item-action>
          <v-list-item-subtitle>Remove filter</v-list-item-subtitle>
        </v-list-item>
      </v-list>
    </v-card>
  </v-menu>
</template>

<script>
import FilterMenu from './FilterMenu.vue'

export default {
  name: 'FilterChip',
  components: {
    FilterMenu,
  },
  props: {
    chip: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      quickTags: [
        { tag: 'bad', color: 'red', textColor: 'white', label: 'mdi-alert-circle-outline' },
        { tag: 'suspicious', color: 'orange', textColor: 'white', label: 'mdi-help-circle-outline' },
        { tag: 'good', color: 'green', textColor: 'white', label: 'mdi-check-circle-outline' },
      ],
    }
  },
  computed: {
    isTimeChip() {
      return !!(this.chip && this.chip.type && this.chip.type.startsWith('datetime'))
    },
  },
  methods: {
    getQuickTag(tag) {
      return this.quickTags.find(function (el) {
        return el.tag === tag
      })
    },
    formatChipDisplay(chip) {
      // Format datetime_range chips nicely
      if (chip && chip.type === 'datetime_range' && chip.value) {
        const dayjs = require('@/plugins/dayjs').default
        const parts = chip.value.split(',')
        const startStr = parts[0]
        const endStr = parts[1]
        if (!startStr) return chip.value

        const userTz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
        const start = dayjs(startStr).tz(userTz)
        const end = endStr ? dayjs(endStr).tz(userTz) : null

        // If same day, show "DD MMM YYYY" format
        if (end && start.format('YYYY-MM-DD') === end.format('YYYY-MM-DD')) {
          return start.format('DD MMM YYYY')
        }
        // If different days, show range
        if (end) {
          return start.format('DD MMM') + ' - ' + end.format('DD MMM YYYY')
        }
        // Single day
        return start.format('DD MMM YYYY')
      }
      // For other chips, return as is
      return chip.field ? chip.field + ' : ' + chip.value : chip.value
    },
  },
}
</script>
