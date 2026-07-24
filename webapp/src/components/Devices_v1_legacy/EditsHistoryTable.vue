// added for WISPR-lab/data-export-gui
<template>
  <div class="mb-6">
    <v-simple-table class="border rounded-xl overflow-hidden">
      <template v-slot:default>
        <thead>
          <tr>
            <th class="text-left text-body-2 font-weight-medium text--primary" style="width: 150px;">Time</th>
            <th class="text-left text-body-2 font-weight-medium text--primary">Action Description</th>
            <th class="text-left text-body-2 font-weight-medium text--primary">Reason</th>
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
                Created new profile <strong>{{ titleCase(log.target_profile_label) }}</strong>
                <span class="text--secondary ml-1 mr-1"> [ID: {{ log.target_profile_id ? log.target_profile_id.substring(0, 4) : '' }}...]</span>
              </span>
              <span v-else-if="log.action_type === 'move_instances'">
                Moved {{ log.instance_ids.length }} instance(s) from profile
                <strong>{{ getProfileLabelById(log.source_profile_id) || titleCase(log.source_profile_label) || 'Deleted Profile' }}</strong>
                <span v-if="log.source_profile_id" class="text--secondary ml-1 mr-1"> [ID: {{ log.source_profile_id.substring(0, 4) }}...]</span>
                to profile 
                <strong>{{ getProfileLabelById(log.target_profile_id) || titleCase(log.target_profile_label) }}</strong>
                <span v-if="log.target_profile_id" class="text--secondary ml-1 mr-1"> [ID: {{ log.target_profile_id.substring(0, 4) }}...]</span>
              </span>
              <span v-else-if="log.action_type === 'delete_profile'">
                Deleted profile <strong>{{ titleCase(log.source_profile_label) }}</strong>
                <span v-if="log.source_profile_id" class="text--secondary ml-1 mr-1"> [ID: {{ log.source_profile_id.substring(0, 4) }}...]</span>
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
import { titleCase } from '@/filters/TitleCase.js';

export default {
  name: 'EditsHistoryTable',
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
    titleCase(str) {
      return titleCase(str);
    },
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
        return titleCase(p.user_label) || titleCase(p.model || 'Unknown Profile');
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
.v-data-table >>> th,
.v-data-table >>> td {
  padding-left: 24px !important;
  padding-right: 24px !important;
}
</style>
