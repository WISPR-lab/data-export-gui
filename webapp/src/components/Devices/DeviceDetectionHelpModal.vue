<template>
  <v-dialog v-model="isOpen" width="600">
    <v-card>
      <v-card-title>
        How we detect and group your devices
      </v-card-title>
      <v-card-text class="pa-6">
        <p>
          we group the devices in two ways. an instance and a profile are just a group of records. instance is group. profile is a super group
        </p>
        <div class="mb-4">
          <div class="subtitle-2 font-weight-bold">Device Instance</div>
          <div class="body-2 text--secondary">
            Either: (1) A trusted or registered device (e.g., registered for 2FA). (2) A group of login events linked by a common identifier (like a cookie or app token) or tracked across browser/client upgrades.
          </div>
        </div>
        <div class="mb-4">
          <div class="subtitle-2 font-weight-bold">Device Profile</div>
          <div class="body-2 text--secondary">
            A super-group of one or more device instances that share the same hardware model (e.g., Apple iPhone 11). Since identical hardware models are grouped automatically, you can rename, edit, or split them apart if they represent different physical devices.
          </div>
        </div>
        <p>
          If your device exported a serial number or hardware ID, we use that as a definitive match to link instances. We also parse user agents to identify device model and OS versions. If you have multiple physical devices of the same model (like two Samsung Galaxy S22s), you can use the editing controls to split their instances into separate profiles.
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
