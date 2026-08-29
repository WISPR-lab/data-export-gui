<!-- modified for anonymous-research-group/data-export-gui -->
<template>
  <div v-if="iconOnly" class="pa-4" style="cursor: pointer" @click="$emit('toggleDrawer'); expanded = true">
    <v-badge :content="compareEvents.length" color="primary" overlap :value="compareEvents.length > 0">
      <v-icon left>mdi-scale-balance</v-icon>
    </v-badge>
    <div style="height: 1px"></div>
  </div>
  <div v-else id="tsLeftPanelCompareEvents">
    <v-divider class="mb-0"></v-divider>
    <div
      style="cursor: pointer"
      class="pa-4 d-flex align-center justify-space-between"
      @click="toggleExpand"
      :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'"
    >
      <span> <v-icon left>mdi-scale-balance</v-icon> Compare events </span>
      <div class="d-flex align-center">
        <small v-if="compareEvents.length > 0">
          <strong>{{ compareEvents.length }}</strong>
        </small>
        <v-btn v-else icon x-small @click.stop="helpDialog = true" title="How event comparison works">
          <v-icon small color="grey">mdi-help-circle-outline</v-icon>
        </v-btn>
      </div>
    </div>

    <!--=Help  Dialog -->
    <v-dialog v-model="helpDialog" max-width="450">
      <v-card class="rounded-xl">
        <v-card-title class="d-flex justify-space-between align-center text-h6 font-weight-bold pt-4 pb-2 px-6">
          <span>Event Comparison</span>
          <v-btn icon small @click="helpDialog = false" title="Close dialog">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text class="text-body-2 text--secondary px-6 pb-6 pt-2" style="line-height: 1.6;">
          Select <strong>"Pin for comparison"</strong> in any event's  menu <v-icon small>mdi-dots-vertical</v-icon> to pin up to 5 events and compare their attributes side-by-side.
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-expand-transition>
      <div v-show="expanded && compareEvents.length" class="px-4 pb-4">
        <!-- Minimal Selected Events List -->
        <div
          v-for="(item, idx) in compareEvents"
          :key="item._id || idx"
          style="cursor: pointer; font-size: 0.9em"
        >
          <v-row
            no-gutters
            class="py-2 px-2 d-flex align-center justify-space-between mb-1"
            :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'"
          >
            <span
              class="text-truncate mr-2"
              style="max-width: calc(100% - 28px)"
              :title="formatEventRow(item)"
            >
              {{ formatEventRow(item) }}
            </span>
            <v-btn icon x-small @click.stop="removeEvent(item._id)" title="Unpin event">
              <v-icon x-small>mdi-close</v-icon>
            </v-btn>
          </v-row>
        </div>

        <!-- Half-and-half Side-by-side Action Buttons -->
        <div class="d-flex align-center mt-3" style="gap: 8px;">
          <v-btn
            small
            color="primary"
            style="flex: 1;"
            :disabled="compareEvents.length &lt; 2"
            @click="openCompareDialog"
          >
            Compare
          </v-btn>
          <v-btn text small color="grey darken-1" style="flex: 1;" @click="clearAll">
            Clear all
          </v-btn>
        </div>
      </div>
    </v-expand-transition>
  </div>
</template>

<script>
export default {
  name: 'CompareEvents',
  props: {
    iconOnly: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      expanded: true,
      helpDialog: false,
    }
  },
  computed: {
    compareEvents() {
      return this.$store.state.compareEvents || []
    },
  },
  methods: {
    toggleExpand() {
      if (this.compareEvents.length > 0) {
        this.expanded = !this.expanded
      } else {
        this.helpDialog = true
      }
    },
    openCompareDialog() {
      this.$store.commit('SET_SHOW_COMPARE_DIALOG', true)
    },
    removeEvent(eventId) {
      this.$store.commit('REMOVE_COMPARE_EVENT', eventId)
    },
    clearAll() {
      this.$store.commit('CLEAR_COMPARE_EVENTS')
    },
    formatEventRow(ev) {
      if (!ev || !ev._source) return 'Event'
      const ts = ev._source.primary_timestamp || ev._source.datetime || ''
      let formattedTs = ts
      if (ts && this.$options.filters && this.$options.filters.shortDateTimeLocal) {
        formattedTs = this.$options.filters.shortDateTimeLocal(ts)
      }
      const actionMsg =
        ev._source.event_type_msg ||
        ev._source.event_type ||
        ev._source.action ||
        ev._source.message ||
        ev._source.summary ||
        ev._source.title ||
        ''
      return actionMsg ? `${formattedTs} - ${actionMsg}` : formattedTs
    },
  },
}
</script>

<style scoped lang="scss"></style>
