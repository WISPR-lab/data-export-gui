<template>
  <div v-if="showTour" class="tour-overlay">
    <div class="tour-spotlight" :style="spotlightStyle"></div>
    <v-card class="rounded" elevation="4" :style="tooltipStyle">
      <v-card-text class="pa-6">
        <h3 class="text-h5 font-weight-bold secondary--text mb-4">{{ heading }}</h3>
        <p class="text-body1 secondary--text">
          <slot></slot>
        </p>
      </v-card-text>
      <v-card-actions class="pa-4">
        <v-btn text @click="onExit">Exit tour</v-btn>
        <v-spacer></v-spacer>
        <v-btn color="primary" @click="onNext">Next</v-btn>
      </v-card-actions>
    </v-card>
  </div>
</template>

<script>
import { completeTour, shouldShowTour } from '@/utils/tourState';

export default {
  name: 'BaseTour',
  props: {
    heading: {
      type: String,
      required: true,
    },
    elementId: {
      type: String,
      required: true,
    },
    tourKey: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      showTour: false,
      spotlightStyle: {},
      tooltipStyle: {},
    };
  },
  created() {
    const hasData = this.$store.state.sketch.timelines && this.$store.state.sketch.timelines.length > 0;
    const hashPart = window.location.hash.split('?')[1] || '';
    const debugMode = new URLSearchParams(hashPart).get('debugTourSearch') === 'true';
    
    this.updateTourVisibility(hasData, debugMode);
    
    this.onTourCompleted = () => {
      const hasData = this.$store.state.sketch.timelines && this.$store.state.sketch.timelines.length > 0;
      const hashPart = window.location.hash.split('?')[1] || '';
      const debugMode = new URLSearchParams(hashPart).get('debugTourSearch') === 'true';
      this.updateTourVisibility(hasData, debugMode);
    };
    this.boundUpdateSpotlight = () => this.updateSpotlight();
    window.addEventListener('tourCompleted', this.onTourCompleted);
  },
  methods: {
    updateTourVisibility(hasData, debugMode) {
      if (!hasData) {
        this.showTour = false;
        return;
      }
      
      const shouldShow = debugMode || shouldShowTour(this.tourKey);
      
      if (shouldShow && !this.showTour) {
        this.showTour = true;
        this.$nextTick(() => {
          this.updateSpotlight();
          window.addEventListener('resize', this.boundUpdateSpotlight);
        });
      } else if (!shouldShow && this.showTour) {
        this.showTour = false;
        window.removeEventListener('resize', this.boundUpdateSpotlight);
      }
    },
    updateSpotlight() {
      const element = document.getElementById(this.elementId);
      if (!element) return;

      const cardElement = element.closest('.v-card');
      const targetElement = cardElement || element;
      
      const rect = targetElement.getBoundingClientRect();
      const padding = 12;
      
      this.spotlightStyle = {
        position: 'fixed',
        top: `${rect.top - padding}px`,
        left: `${rect.left - padding}px`,
        width: `${rect.width + padding * 2}px`,
        height: `${rect.height + padding * 2}px`,
        borderRadius: '8px',
        boxShadow: '0 0 0 9999px rgba(0,0,0,0.7)',
        zIndex: '9998',
        pointerEvents: 'none',
      };

      const gap = 16;
      
      this.tooltipStyle = {
        position: 'fixed',
        top: `${rect.bottom + gap}px`,
        left: `${Math.max(16, rect.left)}px`,
        maxWidth: '400px',
        zIndex: '9999',
      };
    },
    onNext() {
      completeTour(this.tourKey);
      this.$emit('complete');
    },
    onExit() {
      completeTour(this.tourKey);
      this.$emit('complete');
    },
  },
  beforeDestroy() {
    if (this.boundUpdateSpotlight) {
      window.removeEventListener('resize', this.boundUpdateSpotlight);
    }
    if (this.onTourCompleted) {
      window.removeEventListener('tourCompleted', this.onTourCompleted);
    }
  },
};
</script>

<style scoped>
.tour-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9997;
}
</style>
