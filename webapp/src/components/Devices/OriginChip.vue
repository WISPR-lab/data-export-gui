<template>
  <v-chip :key="`${origin.origin}-${origin.upload_id}`">
    <v-icon :color="chipColor" left small>mdi-circle</v-icon>
    {{ formatOriginText }}
  </v-chip>
</template>

<script>
export default {
  name: 'OriginChip',
  props: {
    origin: {
      type: Object,
      required: true
    }
  },
  computed: {
    formatOriginText() {
      if (typeof this.origin === 'string') {
        return this.origin.replace('/', ' / ');
      }
      return (this.origin.origin || '').replace('/', ' / ');
    },
    chipColor() {
      if (typeof this.origin === 'object' && this.origin.color) {
        const color = String(this.origin.color);
        if (color.length > 0 && color[0] !== '#') {
          return '#' + color;
        }
        return color;
      }
      return '#5E75C2';
    }
  }
}
</script>
