<template>
  <v-row no-gutters align="center">
    <!-- Drag Handle and Icon -->
    <v-icon v-if="isGeneric" color="grey darken-1" class="mr-4">mdi-drag-vertical</v-icon>
    <v-avatar size="40" color="grey lighten-4" class="mr-4" :class="{'white border': isGeneric}">
      <v-icon color="grey darken-2" small>
        {{ isGeneric ? 'mdi-help-circle-outline' : (device.icon || 'mdi-cellphone') }}
      </v-icon>
    </v-avatar>
    
    <!-- Text Labels -->
    <v-col class="mr-4">
      <div v-if="!isGeneric" class="subtitle-1 font-weight-bold">
        {{ device.user_label || device.model }}
        <span v-if="device.user_label && device.model" class="grey--text text--darken-2 body-2 font-weight-regular ml-1">
          ({{ device.model }})
        </span>
      </div>
      <div v-else class="subtitle-1 font-weight-bold">
        {{ device.label }}
      </div>
      <div class="body-2 grey--text text--darken-2">
        <span>{{ device.manufacturer || 'Unknown' }} <span v-if="device.location">&bull; Last seen in {{ device.location }}</span></span>
      </div>
    </v-col>

    <!-- Origin Chips (horizontal) -->
    <div v-if="device.origins && device.origins.length > 0" class="d-flex align-center mr-4">
      <v-chip
        v-for="(origin, idx) in device.origins"
        :key="idx"
        class="mr-2"
      >
        <v-icon :color="getChipColor(origin)" left>mdi-circle</v-icon>
        {{ formatOriginText(origin) }}
      </v-chip>
    </div>

    <!-- Side Status/Action -->
    <v-col v-if="!open" cols="auto" class="text-right d-flex align-center">
      <!-- <v-chip v-if="!isGeneric && device.status === 'Needs Review'" small color="orange darken-3" dark class="font-weight-bold px-2" style="height: 24px;">
        Review needed
      </v-chip> -->
      <div v-if="isGeneric" class="caption grey--text text--darken-1 font-weight-bold text-uppercase px-2">
        Drag to group
      </div>
    </v-col>
  </v-row>
</template>

<script>
export default {
  name: 'DeviceHeader',
  props: {
    device: {
      type: Object,
      required: true
    },
    isGeneric: {
      type: Boolean,
      default: false
    },
    open: {
      type: Boolean,
      default: false
    },
    isHighlighted: {
      type: Boolean,
      default: false
    }
  },
  methods: {
    formatOriginText(origin) {
      // Format as "platform/category" or just use the origin string
      if (typeof origin === 'string') {
        return origin.replace('/', ' / ');
      }
      return (origin.origin || '').replace('/', ' / ');
    },
    getChipColor(origin) {
      // Get color from upload if available, otherwise use default
      if (typeof origin === 'object' && origin.color) {
        const color = origin.color;
        if (!color.startsWith('#')) {
          return '#' + color;
        }
        return color;
      }
      return '#5E75C2'; // default color if no upload color found
    }
  }
}
</script>
