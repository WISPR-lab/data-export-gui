<template>
  <base-tour
    heading="Search Your Events"
    elementId="tsSearchInput"
    :tourKey="TOUR_KEYS.EXPLORE_SEARCH_TOUR"
  >
    Search through events and account activity via keywords. Press Enter to search, or use the 
    <v-icon small class="mx-1">mdi-help-circle-outline</v-icon>
    icon to learn more about advanced syntax.
  </base-tour>
</template>

<script>
import BaseTour from './BaseTour.vue';
import { TOUR_KEYS } from '@/utils/tourState';

export default {
  name: 'SearchTour',
  components: { BaseTour },
  computed: {
    TOUR_KEYS() {
      return TOUR_KEYS;
    },
  },
};
</script>
