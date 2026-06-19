<!--
UploadProgressDialog.vue

Extracted progress spinner. Cleaner separation from form logic.
Displays status, progress bar, and current step message.
-->
<template>
  <v-dialog v-model="isOpen" persistent width="500">
    <v-card flat class="pa-6">
      <div class="d-flex align-center mb-4">
        <v-progress-circular indeterminate color="primary" size="20" width="2" class="mr-3"></v-progress-circular>
        <span class="text-body1">{{ friendlyStatus }}</span>
      </div>
      <v-progress-linear
        color="primary"
        height="6"
        rounded
        :value="progress"
      ></v-progress-linear>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: 'UploadProgressDialog',
  props: {
    open: {
      type: Boolean,
      required: true,
    },
    progress: {
      type: Number,
      default: 0,
    },
    statusMessage: {
      type: String,
      default: 'Processing...',
    },
  },
  computed: {
    isOpen: {
      get() {
        return this.open;
      },
      set(val) {
        this.$emit('update:open', val);
      },
    },
    friendlyStatus() {
      const map = {
        validating: 'Reading ZIP file...',
        parsing: 'Parsing records...',
        initializing: 'Parsing records...',
        inserting: 'Mapping events...',
        complete: 'Almost done...',
        error: 'Something went wrong',
      };
      return map[this.statusMessage] || 'Processing...';
    },
  },
};
</script>

<style scoped lang="scss">
.text-muted {
  color: rgba(0, 0, 0, 0.54);
}

:deep(.v-application--dark) {
  .text-muted {
    color: rgba(255, 255, 255, 0.54);
  }
}
</style>
