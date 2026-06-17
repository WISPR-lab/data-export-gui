// added for WISPR-lab/data-export-gui
<template>
  <div class="mt-12 mb-6">
    <h3 class="text-h6 font-weight-bold mb-2 text--primary">History of Manual Changes</h3>
    <p class="text-body-2 text--secondary mb-4">
      Logs when you manually move a <strong>device instance</strong> (a specific app installation or browser telemetry stream, like Instagram or Safari) to a different <strong>device profile</strong> (which groups instances by hardware model, like Apple iPhone 11).
    </p>
 
    <v-simple-table class="border rounded-xl overflow-hidden">
      <template v-slot:default>
        <thead>
          <tr>
            <th class="text-left" style="width: 150px;">Time</th>
            <th class="text-left">Action Description</th>
            <th class="text-left">Reason</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="historyLogs.length === 0">
            <td colspan="3" class="text-center text--secondary font-italic py-4">None yet!</td>
          </tr>
          <tr v-for="log in historyLogs" :key="log.id" v-else>
            <td class="text-no-wrap text-body-2 text--secondary">
              {{ formatLogTime(log.created_at) }}
            </td>
            <td class="text-body-2 py-2 text--primary">
              <span v-if="log.action_type === 'create_profile'">
                Created new profile <strong>{{ log.target_profile_label }}</strong>
                <span class="text-caption text--secondary" style="font-family: monospace;"> [ID: {{ log.target_profile_id ? log.target_profile_id.substring(0, 4) : '' }}...]</span>
              </span>
              <span v-else-if="log.action_type === 'move_instances'">
                Moved {{ log.instance_ids.length }} instance(s) from 
                <strong>{{ getProfileLabelById(log.source_profile_id) || log.source_profile_label || 'Deleted Profile' }}</strong>
                <span v-if="log.source_profile_id" class="text-caption text--secondary" style="font-family: monospace;"> [ID: {{ log.source_profile_id.substring(0, 4) }}...]</span>
                to 
                <strong>{{ getProfileLabelById(log.target_profile_id) || log.target_profile_label }}</strong>
                <span v-if="log.target_profile_id" class="text-caption text--secondary" style="font-family: monospace;"> [ID: {{ log.target_profile_id.substring(0, 4) }}...]</span>
              </span>
            </td>
            <td class="text-body-2 text--secondary font-italic">
              {{ log.reason }}
            </td>
          </tr>
        </tbody>
      </template>
    </v-simple-table>
  </div>
</template>

<script>
export default {
  name: 'UserDeviceEditsTable',
  props: {
    historyLogs: {
      type: Array,
      default: function() { return []; }
    },
    devices: {
      type: Array,
      default: function() { return []; }
    }
  },
  methods: {
    formatLogTime(timestamp) {
      if (!timestamp) return '';
      return new Date(timestamp * 1000).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
      });
    },
    getProfileLabelById(profileId) {
      if (!profileId) return '';
      const p = this.devices.find(function(d) { return d.id === profileId; });
      if (p) {
        return p.user_label || p.model || 'Unknown Profile';
      }
      return '';
    }
  }
}
</script>

<style scoped>
.border {
  border: 1px solid rgba(0,0,0,0.12) !important;
}
.rounded-xl {
  border-radius: 12px !important;
}
</style>
