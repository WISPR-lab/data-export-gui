// added for WISPR-lab/data-export-gui
<template>
  <v-dialog v-model="internalValue" max-width="500px" @input="onDialogInput">
    <!-- Main Group / Move Card -->
    <v-card v-if="!deleteWarningDialog">
      <v-toolbar flat dense color="grey lighten-4" height="64">
        <v-toolbar-title class="text-h6 font-weight-medium text--primary ml-2">
          {{ mode === 'create' ? 'Create New Profile' : 'Move to Existing Profile' }}
        </v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon @click="cancel" :disabled="isLoading">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text class="pa-6">
        <v-alert v-if="error" type="error" outlined dense class="mb-4">
          <div class="text-body-2">{{ error }}</div>
        </v-alert>

        <div v-if="mode === 'move'" class="text-body-2 text--primary mb-4">
          This operation assigns the selected <strong>{{ selectedInstanceIdsToMove.length }} instance(s)</strong> to the destination profile. If the source profile is left empty, it will be deleted.
        </div>

        <div v-if="mode === 'create'" class="text-body-2 text--primary mb-4">
          This operation creates a new profile with the name you provide and maps the selected <strong>{{ selectedInstanceIdsToMove.length }} instance(s)</strong> to it.
        </div>

        <!-- Create Profile Mode -->
        <div v-if="mode === 'create'" class="mb-4">
          <div class="text-body-2 font-weight-medium text--primary mb-1">New Profile Name</div>
          <v-text-field
            v-model="newProfileLabel"
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
          <div class="text-body-2 font-weight-medium text--primary mb-1">Destination Profile</div>
          <v-select
            v-model="destinationProfileId"
            :items="profileItems"
            placeholder="Select"
            outlined
            denselabel="Select Destination Profile" 
            required
            class="rounded-lg"
            hide-details
          ></v-select>
        </div>

        <!-- Required Reason Text Area -->
        <div class="mb-4 mt-4">
          <div class="text-body-2 font-weight-medium text--primary mb-1">Reason</div>
          <v-textarea
            v-model="reason"
            placeholder="Optional: Provide a reason for editing instance(s)"
            outlined
            dense
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

    <!-- Delete Profile Warning Card (Replaces main card in-place) -->
    <v-card v-else>
      <v-toolbar flat dense color="grey lighten-4" height="64">
        <v-toolbar-title class="text-h6 font-weight-medium text--primary ml-2">
          Profile Deletion Warning
        </v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon @click="cancelDeleteWarning">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>
      <v-card-text class="pa-6">
        <div class="d-flex align-start">
          <v-icon color="orange" large class="mr-4 mt-1">mdi-alert-circle-outline</v-icon>
          <div class="text-body-1 text--primary" style="line-height: 1.5;">
            Moving these instance(s) will leave the profile <strong>{{ sourceProfileName }}</strong> empty, which will delete the profile.
            <br><br>
            Are you sure you want to proceed?
          </div>
        </div>
      </v-card-text>
      <v-divider></v-divider>
      <v-card-actions class="pa-4">
        <v-spacer></v-spacer>
        <v-btn text @click="cancelDeleteWarning" class="text-none">
          Cancel
        </v-btn>
        <v-btn color="primary" @click="proceedWithGroup" class="text-none px-6" :loading="isLoading">
          Proceed
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { checkMoveEligibility } from '@/database/queries/user_device_edits.js';
import { titleCase } from '@/filters/TitleCase.js';

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
    sourceProfileId: {
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
      destinationProfileId: '',
      reason: '',
      deleteWarningDialog: false,
      warningProceeded: false,
    };
  },
  watch: {
    value(val) {
      if (val) {
        // Reset fields when dialog opens
        this.newProfileLabel = '';
        this.destinationProfileId = '';
        this.reason = '';
        this.deleteWarningDialog = false;
        this.warningProceeded = false;
      }
    }
  },
  computed: {
    internalValue: {
      get() { return this.value; },
      set(val) { this.$emit('input', val); }
    },
    selectedInstances() {
      const instances = [];
      const self = this;
      this.selectedInstanceIdsToMove.forEach(function(id) {
        let found = null;
        self.existingProfiles.forEach(function(p) {
          if (p.instances) {
            const inst = p.instances.find(function(i) { return i.id === id; });
            if (inst) found = inst;
          }
        });
        if (found) {
          instances.push(found);
        }
      });
      return instances;
    },
    willSourceProfileBeEmptied() {
      if (!this.sourceProfileId) return false;
      const srcProfile = this.existingProfiles.find(p => p.id === this.sourceProfileId);
      if (!srcProfile || !srcProfile.instances) return false;
      return this.selectedInstanceIdsToMove.length === srcProfile.instances.length;
    },
    sourceProfileName() {
      if (!this.sourceProfileId) return '';
      const srcProfile = this.existingProfiles.find(p => p.id === this.sourceProfileId);
      if (srcProfile) {
        return srcProfile.user_label || titleCase(srcProfile.model || 'Unknown Profile');
      }
      return '';
    },
    profileItems() {
      const self = this;
      return this.existingProfiles
        .filter(function(p) { return p.id !== self.sourceProfileId; })
        .map(function(p) {
          const eligibility = checkMoveEligibility(p, self.selectedInstances);
          const modelName = titleCase(p.model || 'Unknown Model');
          let labelText = '';
          if (p.user_label) {
            labelText = p.user_label + ' (' + modelName + ')';
          } else {
            labelText = modelName;
          }
          
          if (p.id) {
            labelText += ' [ID: ' + p.id.substring(0, 8) + ']';
          }

          if (p.instances && p.instances.length) {
            labelText += ' - ' + p.instances.length + ' instance(s)';
          }

          if (!eligibility.isEligible) {
            labelText += ' - Incompatible (' + eligibility.reason + ')';
          }

          return {
            text: labelText,
            value: p.id,
            disabled: !eligibility.isEligible
          };
        });
    },
    isValid() {
      if (this.mode === 'create') {
        return (this.newProfileLabel || '').trim().length > 0;
      } else if (this.mode === 'move') {
        return !!this.destinationProfileId;
      }
      return false;
    }
  },
  methods: {
    submit() {
      if (!this.isValid) return;

      if (this.willSourceProfileBeEmptied && !this.warningProceeded) {
        this.deleteWarningDialog = true;
        return;
      }

      this.$emit('confirm', {
        mode: this.mode,
        newProfileLabel: this.newProfileLabel.trim(),
        targetProfileId: this.destinationProfileId,
        reason: this.reason.trim()
      });
      this.warningProceeded = false;
    },
    cancel() {
      this.$emit('input', false);
    },
    onDialogInput(val) {
      if (!val) {
        this.$emit('closed');
      }
    },
    cancelDeleteWarning() {
      this.deleteWarningDialog = false;
    },
    proceedWithGroup() {
      this.deleteWarningDialog = false;
      this.warningProceeded = true;
      this.submit();
    }
  }
}
</script>
