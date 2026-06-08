// added for WISPR-lab/data-export-gui
<template>
  <v-card outlined class="pa-4 d-flex align-center" style="gap: 16px; background-color: white;">
    <!-- UA summary chip — same style as DeviceHeader origin chips -->
    <div class="d-flex flex-wrap align-center" style="gap: 4px; flex: 0 0 auto;">
      <OriginChip v-if="atomic.ua_summary" :summary="atomic.ua_summary" />
      <v-chip v-else small>
        <v-icon :color="atomic.upload_color || '#5E75C2'" left small>mdi-circle</v-icon>
        {{ (atomic.platform || 'Unknown').toUpperCase() }}
      </v-chip>
    </div>

    <!-- Client Name & Version & OS & Timeline -->
    <div class="flex-grow-1 text-truncate">
      <div class="body-2 font-weight-bold">{{ getClientLabel | formatDeviceDetails }}</div>
      <div class="caption grey--text text--darken-2">
        OS: {{ getOSLabel | formatDeviceDetails }} &bull; {{ getTimelineString }} &bull; {{ atomic.event_count || 0 }} events
      </div>
    </div>

    <!-- Actions -->
    <div class="d-flex align-center" style="gap: 8px;">
      <v-btn
        v-if="atomic.event_count > 0"
        text
        small
        color="primary"
        @click.stop="goToExplore"
        title="View events for this instance"
      >
        View Events
        <v-icon right small>mdi-arrow-right</v-icon>
      </v-btn>

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
    </div>
  </v-card>
</template>

<script>
import OriginChip from './OriginChip.vue';

export default {
  name: 'AtomicDeviceRecord',
  components: { OriginChip },
  props: {
    atomic: {
      type: Object,
      required: true
    }
  },
  computed: {
    getClientLabel() {
      const name = this.atomic.client_name || 'Unknown Client';
      if (this.atomic.latest_client_version) {
        return `${name} (v${this.atomic.latest_client_version})`;
      }
      return name;
    },
    getOSLabel() {
      const os = this.atomic.os_type || this.atomic.os_name || 'Unknown OS';
      if (this.atomic.latest_os_version) {
        return `${os.toUpperCase()} ${this.atomic.latest_os_version}`;
      }
      return os.toUpperCase();
    },
    getTimelineString() {
      if (!this.atomic.first_seen || !this.atomic.last_seen) return '';
      const start = new Date(this.atomic.first_seen * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
      const end = new Date(this.atomic.last_seen * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
      return start === end ? start : `${start} – ${end}`;
    }
  },
  methods: {
    goToExplore() {
      const queryString = `device_instance_id:${this.atomic.id}`;
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
.cursor-pointer {
  cursor: pointer;
}
</style>
