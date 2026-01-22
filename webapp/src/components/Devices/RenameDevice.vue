<template>
  <div>
    <h3>Label device</h3>
    <br />
    <v-form @submit.prevent="renameDevice()">
      <v-text-field
        outlined
        dense
        autofocus
        v-model="newDeviceLabel"
        @focus="$event.target.select()"
        clearable
        :rules="deviceLabelRules"
        placeholder="e.g., Work Laptop, iPhone"
      >
      </v-text-field>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn text @click="closeDialog()"> Cancel </v-btn>
        <v-btn 
          :disabled="!newDeviceLabel || newDeviceLabel.length > 255" 
          text 
          color="primary" 
          @click="renameDevice()"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-form>
  </div>
</template>

<script>
export default {
  data() {
    return {
      newDeviceLabel: '',
      deviceLabelRules: [
        (v) => !v || v.length <= 255 || 'Label is too long.',
      ],
    }
  },
  props: {
    device: {
      type: Object,
      required: true,
    },
  },
  methods: {
    renameDevice() {
      // Emit event with the new label
      this.$emit('device-labeled', {
        deviceId: this.device.id,
        label: this.newDeviceLabel,
      })
      this.$emit('close')
    },
    closeDialog() {
      this.newDeviceLabel = this.device.label || ''
      this.$emit('close')
    },
  },
  created() {
    this.newDeviceLabel = this.device.label || ''
  },
}
</script>

<!-- CSS scoped to this component only -->
<style scoped lang="scss"></style>
