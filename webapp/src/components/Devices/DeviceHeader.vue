// added for WISPR-lab/data-export-gui
<template>
  <v-row no-gutters align="center" class="py-2">
    <!-- Drag Handle and Icon -->
    <v-icon v-if="isGeneric" color="grey--darken-1" class="mr-4">mdi-drag-vertical</v-icon>
    <v-avatar size="40" color="grey--lighten-4" class="mr-3" :class="{'white border': isGeneric}">
      <v-icon color="grey--darken-3" small>
        {{ isGeneric ? 'mdi-help-circle-outline' : (device.icon || 'mdi-cellphone') }}
      </v-icon>
    </v-avatar>
    
    <!-- Text Labels -->
    <v-col class="mr-4 min-width-0">
      <div v-if="!isGeneric" class="subtitle-1 font-weight-bold text-truncate">
        {{ (device.user_label || device.model) | formatDeviceDetails }}
        <span v-if="device.user_label && device.model" class="grey--text text--darken-3 body-2 font-weight-regular ml-1">
          ({{ device.model | formatDeviceDetails }})
        </span>
      </div>
      <div v-else class="subtitle-1 font-weight-bold text-truncate">
        {{ device.label | formatDeviceDetails }}
      </div>
      <div class="body-2 grey--text text--darken-3 text-truncate">
        <span>{{ (device.manufacturer || 'Unknown') | formatDeviceDetails }} &bull; {{ latestOSLabel | formatDeviceDetails }} <span v-if="activeDateRange">&bull; {{ activeDateRange }}</span></span>
      </div>
    </v-col>

    <!-- Origin Chips (horizontal) -->
    <v-col cols="auto" v-if="device.ua_summaries && device.ua_summaries.length > 0" class="d-flex align-center flex-wrap mr-4" style="gap: 4px;">
      <OriginChip
        v-for="(summary, idx) in device.ua_summaries"
        :key="idx"
        :summary="summary"
      />
    </v-col>

    <!-- Side Status/Action -->
    <v-col cols="auto" class="d-flex align-center" style="gap: 8px;">
      <!-- <div v-if="!open && isGeneric" class="caption grey--text text--darken-1 font-weight-bold text-uppercase">
        Drag to group
      </div> -->
      <!-- <v-btn icon @click.stop="$emit('showJSON')" title="View raw data">
        <v-icon>mdi-code-braces</v-icon>
      </v-btn> -->

      <v-tooltip bottom>
        <template v-slot:activator="{ on, attrs }">
          <v-btn
            v-bind="attrs"
            v-on="on"
            icon
            medium
            @click.stop="$emit('showJSON', device)"
            title="View raw data"
            class="ml-1 mr-1"
          >
            <v-icon>mdi-code-braces</v-icon>
          </v-btn>
        </template>
        <span>View raw data</span>
      </v-tooltip>
    </v-col>
  </v-row>
</template>

<script>
import OriginChip from './OriginChip.vue';

export default {
  name: 'DeviceHeader',
  components: {
    OriginChip
  },
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
    latestOSLabel() {
      const instances = this.device.instances || [];
      const sorted = [...instances].sort((a, b) => (b.last_seen || 0) - (a.last_seen || 0));
      const latest = sorted[0];
      if (!latest) return this.device.os_type || '';
      const os = (latest.os_type || latest.os_name || '').toUpperCase();
      const ver = latest.latest_os_version || '';
      return ver ? `${os} ${ver}` : os;
    },
    activeDateRange() {
      const { first_seen, last_seen } = this.device;
      if (!first_seen || !last_seen) return '';
      const fmt = ts => new Date(ts * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
      const start = fmt(first_seen);
      const end = fmt(last_seen);
      return start === end ? start : `${start} – ${end}`;
    }
  }
}
</script>
