<template>
  <div class="platforms-list">
    <div v-for="timeline in sketch.timelines" :key="timeline.id" class="platform-row">
      <ts-timeline-component
        :timeline="timeline"
        :is-selected="false"
      >
        <template v-slot:processed="slotProps">
          <div class="platform-content" :style="{ backgroundColor: $vuetify.theme.dark ? '#303030' : '#f5f5f5' }">
            <v-icon
              v-if="!slotProps.timelineFailed"
              :color="slotProps.timelineChipColor"
              size="20"
            >
              mdi-circle
            </v-icon>
            <v-icon
              v-else
              title="Import failed"
              color="red"
              size="20"
            >
              mdi-alert-circle-outline
            </v-icon>
            <span class="text-body-2">{{ timeline.name }}</span>
          </div>
        </template>
      </ts-timeline-component>
      <span class="text-body-3 grey--text text--darken-2" style="font-style: italic;">Last login: 01/01/2026 3:45PM</span>
    </div>
  </div>
</template>

<script>
import TsTimelineComponent from '../Explore/TimelineComponent.vue'

export default {
  name: 'PlatformGrid',
  components: {
    TsTimelineComponent,
  },
  computed: {
    sketch() {
      return this.$store.state.sketch
    },
  },
}
</script>

<style scoped lang="scss">
.platforms-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.platform-row {
  display: grid;
  grid-template-columns: 150px 200px;
  align-items: center;
  gap: 8px;
}

.platform-content {
  display: flex;
  align-items: center;
  gap: 12px;
  width: fit-content;
  padding: 4px 12px;
  margin: 0;
  border-radius: 16px;
}

.platform-content v-icon {
  flex-shrink: 0;
}
</style>
