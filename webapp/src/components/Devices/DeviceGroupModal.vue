<template>
  <v-dialog v-model="internalValue" max-width="500px" @input="onDialogInput">
    <v-card v-if="source && target">
      <v-toolbar flat dense color="grey--lighten-4" height="64">
        <v-toolbar-title class="text-h6 font-weight-bold ml-2">{{ success ? 'Merge successful!' : 'Is this the same device?' }}</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon @click="cancel" :disabled="isLoading">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text class="pa-6">
        <v-alert v-if="error" type="error" outlined dense class="mb-4">
          <div class="body-2">{{ error }}</div>
        </v-alert>

        <v-alert v-if="success" type="success" outlined dense class="mb-4">
          <div class="body-2">{{ source.label }} has been merged into {{ target.user_label || target.model }}</div>
        </v-alert>

        <div v-if="!success" class="body-1 mb-4">
          Are you sure you want to combine the activity from <strong>{{ source.label }}</strong> into the <strong>{{ target.user_label || target.model }}</strong> profile?
        </div>
        
        <div v-if="!success" class="body-2 grey--text text--darken-3 italic">
          <v-icon small class="mr-1">mdi-information-outline</v-icon>
          You can undo this later.
        </div>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions class="pa-4">
        <v-spacer></v-spacer>
        <v-btn v-if="!success" text @click="cancel" class="text-none" :disabled="isLoading">
          Cancel
        </v-btn>
        <v-btn v-if="!success" color="primary" @click="confirm" class="text-none px-6" :loading="isLoading" :disabled="isLoading">
          {{ isLoading ? 'Merging...' : 'Merge device data' }}
        </v-btn>
        <v-btn v-if="success" color="primary" @click="cancel" class="text-none px-6">
          Close
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
    source: {
      type: Object,
      default: () => null
    },
    target: {
      type: Object,
      default: () => null
    },
    isLoading: {
      type: Boolean,
      default: false
    },
    error: {
      type: String,
      default: null
    },
    success: {
      type: Boolean,
      default: false
    }
  },
  computed: {
    internalValue: {
      get() { return this.value; },
      set(val) { this.$emit('input', val); }
    }
  },
  methods: {
    confirm() {
      this.$emit('confirm');
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
