<template>
  <v-chip small>
    <v-icon :color="chipColor" left small>mdi-circle</v-icon>
    {{ label }}
  </v-chip>
</template>

<script>
export default {
  name: 'UASummaryChip',
  props: {
    /**
     * A ua_summary dict: { primary: String, secondary: String, color: String }
     * Renders as "Primary (Secondary)" or just "Primary" when secondary is empty.
     */
    summary: {
      type: Object,
      required: true
    }
  },
  computed: {
    label() {
      if (this.summary.platform) {
        return this.summary.platform;
      }
      const p = this.summary.primary || '';
      const s = this.summary.secondary || '';
      return s ? `${p} (${s})` : p;
    },
    chipColor() {
      const color = String(this.summary.color || '');
      if (!color) return '#5E75C2';
      return color[0] !== '#' ? '#' + color : color;
    }
  }
}
</script>
