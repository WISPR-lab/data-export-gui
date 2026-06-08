// added for WISPR-lab/data-export-gui
<template>
  <v-row no-gutters align="center" class="py-2">
    <!-- Drag handle -->
    <v-icon v-if="isGeneric" color="grey--darken-1" class="mr-4">mdi-drag-vertical</v-icon>

    <!-- Device icon -->
    <v-avatar size="40" color="grey--lighten-4" class="mr-3 flex-shrink-0" :class="{'white border': isGeneric}">
      <v-icon color="grey--darken-3" small>
        {{ isGeneric ? 'mdi-help-circle-outline' : (device.icon || 'mdi-cellphone') }}
      </v-icon>
    </v-avatar>

    <!-- Text block: model, manufacturer, activity -->
    <v-col class="min-width-0 mr-4">
      <div v-if="!isGeneric" class="subtitle-1 font-weight-bold text-truncate">
        {{ (device.user_label || device.model) | formatDeviceDetails }}
        <span v-if="device.user_label && device.model" class="grey--text text--darken-3 body-2 font-weight-regular ml-1">
          ({{ device.model | formatDeviceDetails }})
        </span>
      </div>
      <div v-else class="subtitle-1 font-weight-bold text-truncate">
        {{ device.label | formatDeviceDetails }}
      </div>
      <div v-if="device.manufacturer" class="body-2 grey--text text--darken-3">
        {{ device.manufacturer | formatDeviceDetails }}
      </div>
      <div v-if="activityString" class="body-2 grey--text text--darken-3">
        {{ activityString }}
      </div>
    </v-col>

    <!-- UA summary chips — horizontal, wrapping -->
    <v-col v-if="device.ua_summaries && device.ua_summaries.length > 0" cols="auto" class="d-flex flex-wrap align-center mr-4" style="gap: 4px;">
      <UASummaryChip
        v-for="(summary, idx) in device.ua_summaries"
        :key="idx"
        :summary="summary"
      />
    </v-col>
  </v-row>
</template>

<script>
import UASummaryChip from './UASummaryChip.vue';

export default {
  name: 'DeviceProfileHeader',
  components: { UASummaryChip },
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
  computed: {
    activityString() {
      const { first_seen, last_seen } = this.device;
      const fmt = ts => new Date(ts * 1000).toLocaleDateString(undefined, { month: 'short', year: 'numeric' });
      if (first_seen && last_seen) {
        const start = fmt(first_seen);
        const end = fmt(last_seen);
        return start === end ? `Active ${start}` : `Active ${start} \u2013 ${end}`;
      }
      if (first_seen) return `First seen ${fmt(first_seen)}`;
      if (last_seen) return `Last seen ${fmt(last_seen)}`;
      return '';
    }
  }
}
</script>
