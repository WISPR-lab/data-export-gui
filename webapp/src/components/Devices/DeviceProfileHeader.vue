// added for WISPR-lab/data-export-gui
<template>
  <div class="device-header-row py-2">
    <!-- LEFT PART (60% boundary) -->
    <div class="header-left-part">
      <!-- Icon -->
      <div class="header-icon-group">
        <v-avatar size="64" color="grey--lighten-4" class="mr-3 flex-shrink-0">
          <v-icon color="grey--darken-3" size="48">
            {{ device.icon || 'mdi-cellphone' }}
          </v-icon>
        </v-avatar>
      </div>

      <!-- Text block: model, manufacturer, activity -->
      <div class="device-info-col mr-4">
        <div class="text-subtitle-1 font-weight-medium text-truncate text--primary">
          {{ (device.user_label || device.model) | formatDeviceDetails }}
          <span v-if="device.user_label && device.model" class="text-body-2 text--secondary font-weight-regular ml-1">
            ({{ device.model | formatDeviceDetails }})
          </span>
        </div>
        <div v-if="device.manufacturer" class="text-body-2 text--secondary">
          {{ device.manufacturer | formatDeviceDetails }}
        </div>
        <div v-if="activityString" class="text-body-2 text--secondary">
          {{ activityString }}
        </div>
      </div>
    </div>

    <!-- RIGHT PART (40% boundary) -->
    <div class="header-right-part">
      <!-- UA summary chips — horizontal, wrapping -->
      <div v-if="device.ua_summaries && device.ua_summaries.length > 0" class="chip-col-wrap mr-4">
        <UASummaryChip
          v-for="(summary, idx) in device.ua_summaries"
          v-slot:default
          v-if="!summary.isUnknown"
          :key="idx"
          :summary="summary"
        />
      </div>
    </div>
  </div>
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
      const fmt = ts => new Date(ts * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
      if (first_seen && last_seen) {
        const start = fmt(first_seen);
        const end = fmt(last_seen);
        return start === end ? `Active ${start}` : `Active ${start} \u2013 ${end}`;
      }
      if (first_seen) return `First seen ${fmt(first_seen)}`;
      if (last_seen) return `Last seen ${fmt(last_seen)}`;
      return '';
    }
  },
  methods: {
    goToExplore() {
      const queryString = `device_profiles_data:${this.device.id}`;
      const routeName = this.$route.name === 'DemoDevices' ? 'DemoExplore' : 'Explore';
      this.$router.push({
        name: routeName,
        query: { q: queryString }
      });
    }
  }
}
</script>

<style scoped>
.device-header-row {
  display: flex;
  align-items: center;
  width: 100%;
}

.header-left-part {
  width: 60%;
  max-width: 60%;
  flex: 0 0 60%;
  display: flex;
  align-items: center;
}

.header-icon-group {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.device-info-col {
  flex: 1 1 auto;
  min-width: 0;
  text-align: left;
}

.header-right-part {
  width: 40%;
  max-width: 40%;
  flex: 0 0 40%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.chip-col-wrap {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  flex: 1 1 auto;
  min-width: 0;
  row-gap: 8px;
  column-gap: 4px;
}
</style>
