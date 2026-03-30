<template>
  <base-tour
    heading="Main Views"
    elementId="tsMainViewsSection"
    :tourKey="TOUR_KEYS.EXPLORE_MAIN_VIEWS_TOUR"
  >
    Switch between Events (your account activity) and Devices (what accessed your account).
  </base-tour>
</template>

<script>
import BaseTour from './BaseTour.vue';
import { TOUR_KEYS } from '@/utils/tourState';

export default {
  name: 'MainViewsTour',
  components: { BaseTour },
  computed: {
    TOUR_KEYS() {
      return TOUR_KEYS;
    },
  },
};
</script>
