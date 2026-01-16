<!--
UploadProgressDialog.vue

Extracted progress spinner. Cleaner separation from form logic.
Displays status, progress bar, and current step message.
-->
<template>
  <v-dialog v-model="isOpen" persistent width="700">
    <v-card flat class="pa-5">
      <h3 class="mb-4">Processing Your Data Export...</h3>
      <br />
      <v-progress-linear
        color="primary"
        height="25"
        :value="progress"
      >
        {{ progress }}%
      </v-progress-linear>
      <v-divider class="my-4"></v-divider>
      <p class="text-body2 text-muted">
        {{ statusMessage }}
      </p>
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
