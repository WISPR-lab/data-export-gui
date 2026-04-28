<template>
  <v-card outlined class="pa-4 d-flex align-center" style="gap: 16px; background-color: white;">

    <div v-if="atomic.origins && atomic.origins.length > 0" class="d-flex flex-wrap align-center" style="gap: 4px; flex: 0 0 auto;">
      <OriginChip
        v-for="(origin, idx) in atomic.origins"
        :key="`origin-${idx}`"
        :origin="origin"
      />
    </div>
    <div v-else class="d-flex flex-wrap align-center" style="gap: 4px; flex: 0 0 auto;">
      <v-chip small :color="atomic.uploadColor" text-color="white" class="flex-shrink-0">
        {{ atomic.uploadPlatform }}
      </v-chip>
    </div>

    <!-- Model Name -->
    <div class="flex-grow-1 text-truncate">
      <span class="body-2 font-weight-medium">{{ atomic.model }}</span>
    </div>

    <!-- Code Button with Tooltip -->
    <v-tooltip bottom>
      <template v-slot:activator="{ on, attrs }">
        <v-btn
          v-bind="attrs"
          v-on="on"
          icon
          medium
          @click.stop="$emit('showJSON', atomic)"
          title="View raw data"
        >
          <v-icon>mdi-code-braces</v-icon>
        </v-btn>
      </template>
      <span>View raw data</span>
    </v-tooltip>

    <!-- Unlink Button with Tooltip -->
    <v-tooltip bottom>
      <template v-slot:activator="{ on, attrs }">
        <v-btn
          v-bind="attrs"
          v-on="on"
          icon
          medium
          @click="$emit('unmerge', atomic.id)"
          title="Unlink record from profile"
        >
          <v-icon>mdi-link-off</v-icon>
        </v-btn>
      </template>
      <span>Unlink record from profile</span>
    </v-tooltip>
  </v-card>
</template>

<script>
import OriginChip from './OriginChip.vue';
import JSONModal from './JSONModal.vue';

export default {
  name: 'AtomicDeviceRecord',
  components: {
    OriginChip,
    'json-modal': JSONModal
  },
  props: {
    atomic: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
    }
  }
}
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
</style>
