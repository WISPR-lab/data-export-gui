<!-- modified for WISPR-lab/data-export-gui -->
<template>
  <v-slide-y-reverse-transition>
    <v-card
      v-if="compareEvents.length > 0"
      elevation="4"
      class="pinned-event-bar pa-2 px-3 rounded d-flex align-center"
    >
      <v-icon small class="mr-2">mdi-pin-outline</v-icon>

      <span class="text-caption font-weight-medium mr-3" v-if="compareEvents.length < 2">
        {{ compareEvents.length }} event selected (select another to compare)
      </span>
      <span class="text-caption font-weight-medium mr-3" v-else>
        {{ compareEvents.length }} events selected
      </span>

      <v-btn
        v-if="compareEvents.length >= 2"
        color="primary"
        small
        dark
        @click="openCompareDialog"
        class="mr-2"
      >
        Compare
      </v-btn>

      <v-btn icon small @click="clearCompare" title="Clear selection">
        <v-icon small>mdi-close</v-icon>
      </v-btn>
    </v-card>
  </v-slide-y-reverse-transition>
</template>

<script>
export default {
  name: 'PinnedEventBar',
  computed: {
    compareEvents() {
      return this.$store.state.compareEvents || []
    },
  },
  methods: {
    openCompareDialog() {
      this.$store.commit('SET_SHOW_COMPARE_DIALOG', true)
    },
    clearCompare() {
      this.$store.commit('CLEAR_COMPARE_EVENTS')
    },
  },
}
</script>

<style scoped lang="scss">
.pinned-event-bar {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 999;
}
</style>
