<template>
  <v-dialog v-model="isOpen" width="600">
    <v-card>
      <v-card-title>
        How we detect and group your devices
      </v-card-title>
      <v-card-text class="pa-6">
        <p>
            We extract device identifiers from your data in several ways. 
            If your device exported a serial number or hardware ID, we use that as a definitive match. 
        </p><p>
            We also parse user agents to identify device model and OS version. 
            Devices with the same model and version are automatically grouped. 
        </p><p>
            If you have multiple devices of the same type (like two Samsung Galaxy S22s), we'll soon add an unmerge button so you can split them apart.
        </p><p>
            When you click "SEE ALL EVENTS" on a device, we show you all events that match that device's above identifiers. 
            This list may not be comprehensive, as not every event in the dataset has device information attached to it.
        </p>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn text @click="isOpen = false">
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: 'DeviceDetectionHelpModal',
  props: {
    value: {
      type: Boolean,
      default: false
    }
  },
  computed: {
    isOpen: {
      get() {
        return this.value;
      },
      set(val) {
        this.$emit('input', val);
      }
    }
  }
};
</script>
