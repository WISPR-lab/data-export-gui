// added for WISPR-lab/data-export-gui
<template>
  <v-dialog v-model="internalValue" max-width="500px" @input="onDialogInput">
    <v-card>
      <v-toolbar flat dense color="grey lighten-4" height="64">
        <v-toolbar-title class="text-h6 font-weight-bold ml-2">
          {{ mode === 'create' ? 'Create New Profile' : 'Move to Existing Profile' }}
        </v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon @click="cancel" :disabled="isLoading">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text class="pa-6">
        <v-alert v-if="error" type="error" outlined dense class="mb-4">
          <div class="body-2">{{ error }}</div>
        </v-alert>

        <div class="mb-4 body-2 text--secondary">
          Reassigning <strong>{{ selectedInstanceIdsToMove.length }}</strong> instance(s).
        </div>

        <div v-if="mode === 'move'" class="body-2 grey--text text--darken-3 mb-4">
          This operation maps the selected instance(s) to the destination profile. In the database, the corresponding rows in the <code>device_profile_instances</code> table will be updated. If the source profile is left empty, it will be deleted.
        </div>

        <div v-if="mode === 'create'" class="body-2 grey--text text--darken-3 mb-4">
          This operation creates a new profile row in the <code>device_profiles_v2</code> table with the name you provide. The selected instances will be mapped to it via the <code>device_profile_instances</code> table.
        </div>

        <!-- Create Profile Mode -->
        <div v-if="mode === 'create'" class="mb-4">
          <v-text-field
            v-model="newProfileLabel"
            label="New Profile Name"
            placeholder="e.g. Work Phone"
            outlined
            dense
            required
            class="rounded-lg"
            hide-details
          ></v-text-field>
        </div>

        <!-- Move to Profile Mode -->
        <div v-else-if="mode === 'move'" class="mb-4">
          <v-select
            v-model="targetProfileId"
            :items="profileItems"
            label="Select Target Profile"
            outlined
            dense
            required
            class="rounded-lg"
            hide-details
          ></v-select>
        </div>

        <!-- Required Reason Text Area -->
        <div class="mb-4 mt-4">
          <v-textarea
            v-model="reason"
            :label="mode === 'create' ? 'Reason for creating this profile' : 'Reason for moving these instances'"
            placeholder="Required. Provide a technical or personal reason..."
            outlined
            dense
            required
            rows="3"
            class="rounded-lg"
            hide-details
          ></v-textarea>
        </div>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions class="pa-4">
        <v-spacer></v-spacer>
        <v-btn text @click="cancel" class="text-none" :disabled="isLoading">
          Cancel
        </v-btn>
        <v-btn
          color="primary"
          @click="submit"
          class="text-none px-6"
          :loading="isLoading"
          :disabled="isLoading || !isValid"
        >
          Confirm
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: 'DeviceGroupModal',
  props: {
    value: {
      type: Boolean,
      default: false
    },
    mode: {
      type: String,
      default: 'move' // 'move' or 'create'
    },
    selectedInstanceIdsToMove: {
      type: Array,
      default: function() { return []; }
    },
    existingProfiles: {
      type: Array,
      default: function() { return []; }
    },
    currentProfileId: {
      type: String,
      default: ''
    },
    isLoading: {
      type: Boolean,
      default: false
    },
    error: {
      type: String,
      default: null
    }
  },
  data() {
    return {
      newProfileLabel: '',
      targetProfileId: '',
      reason: ''
    };
  },
  watch: {
    value(val) {
      if (val) {
        // Reset fields when dialog opens
        this.newProfileLabel = '';
        this.targetProfileId = '';
        this.reason = '';
      }
    }
  },
  computed: {
    internalValue: {
      get() { return this.value; },
      set(val) { this.$emit('input', val); }
    },
    profileItems() {
      const self = this;
      return this.existingProfiles
        .filter(function(p) { return p.id !== self.currentProfileId; })
        .map(function(p) {
          let labelText = '';
          if (p.user_label) {
            labelText = p.user_label + ' (' + (p.model || 'Unknown Model') + ')';
          } else {
            labelText = (p.model || 'Unknown Model');
          }
          
          if (p.id) {
            labelText += ' [ID: ' + p.id.substring(0, 8) + ']';
          }

          if (p.instances && p.instances.length) {
            labelText += ' - ' + p.instances.length + ' instance(s)';
          }

          return {
            text: labelText,
            value: p.id
          };
        });
    },
    isValid() {
      const cleanReason = (this.reason || '').trim();
      if (!cleanReason) return false;

      if (this.mode === 'create') {
        return (this.newProfileLabel || '').trim().length > 0;
      } else if (this.mode === 'move') {
        return !!this.targetProfileId;
      }
      return false;
    }
  },
  methods: {
    submit() {
      if (!this.isValid) return;
      this.$emit('confirm', {
        mode: this.mode,
        newProfileLabel: this.newProfileLabel.trim(),
        targetProfileId: this.targetProfileId,
        reason: this.reason.trim()
      });
    },
    cancel() {
      this.$emit('input', false);
    },
    onDialogInput(val) {
      if (!val) {
        this.$emit('closed');
      }
    }
  }
}
</script>
