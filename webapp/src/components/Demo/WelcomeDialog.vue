<template>
  <v-dialog :value="value" @input="$emit('input', $event)" width="500" persistent content-class="welcome-dialog-pane">
    <v-card class="pa-5 welcome-card">
      <div class="demo-popover-header">Welcome!</div>
      <div class="demo-popover-content">
        <p>This is where you'll explore your account activity once you upload your data export.</p>
        <p class="mt-4 mb-0">Would you like to try a quick, interactive demo first?</p>
      </div>
      <div class="demo-popover-actions">
        <v-spacer></v-spacer>
        <v-btn text @click="$emit('skip')" class="mr-2">Skip</v-btn>
        <v-btn color="primary" depressed @click="$emit('start')" class="font-weight-bold">Try Demo</v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: 'WelcomeDialog',
  props: {
    value: {
      type: Boolean,
      default: false
    }
  }
}
</script>

<style lang="scss">
.welcome-dialog-pane {
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3) !important;
  border-radius: 12px !important;
}

.welcome-card {
  border-radius: 12px !important;
  border: 1px solid rgba(0, 0, 0, 0.05) !important;
  background: white !important;
}

.demo-popover-header {
  font-weight: 800;
  font-size: 1.2em;
  margin-bottom: 10px;
  color: #1976d2;
  letter-spacing: -0.5px;
}

.demo-popover-content {
  font-size: 1em;
  line-height: 1.5;
  color: #444;
  margin-bottom: 20px;
}

.demo-popover-actions {
  display: flex;
  align-items: center;
  border-top: 1px solid #f0f0f0;
  padding-top: 15px;
}
</style>
