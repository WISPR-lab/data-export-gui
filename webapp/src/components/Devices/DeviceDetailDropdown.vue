<template>
  <div class="pa-6">
    <!-- Optional Explanation Header -->
    <!-- <p v-if="isGeneric" class="body-2 grey--text text--darken-4 mb-6">
      This record could not be automatically linked to a specific hardware model. This often happens when using private browsing mode or a different browser.
    </p> -->

    <!-- 1. Custom Name (Only for confirmed devices) -->
    <div v-if="!isGeneric" class="mb-6">
      <v-text-field
        v-model="device.customLabel"
        placeholder="Give this device a name (e.g. Work Phone)"
        outlined
        dense
        background-color="white"
        prepend-inner-icon="mdi-pencil"
        class="rounded-lg"
        hide-details
        style="max-width: 500px;"
      ></v-text-field>
    </div>

    <v-divider v-if="!isGeneric" class="mb-6"></v-divider>

    <!-- 2. Device Details -->
    <div class="mb-6">
      <div class="overline mb-2">Device details</div>
      <v-row no-gutters>
        <v-col cols="12" sm="4" class="mb-2">
          <div class="body-2 grey--text text--darken-1">Manufacturer</div>
          <div v-if="device.manufacturer" class="body-1">{{ device.manufacturer }}</div>
          <div v-else class="body-1 text-italic grey--text">Unknown</div>
        </v-col>
        <v-col cols="12" sm="4" class="mb-2">
          <div class="body-2 grey--text text--darken-1">Model</div>
          <div class="body-1">{{ isGeneric ? device.label : device.model }}</div>
        </v-col>
        <v-col cols="12" sm="4" class="mb-2">
          <div class="body-2 grey--text text--darken-1">Software</div>
          <div class="body-1">
            {{ Array.isArray(device.osHistory) ? device.osHistory.join(', ') : (device.os || 'Unknown') }}
          </div>
        </v-col>
      </v-row>
    </div>

    <v-divider class="mb-6"></v-divider>

    <!-- 3. Sign-in activity -->
    <div class="mb-6">
      <div class="overline mb-2">Sign-in activity</div>
      <div class="body-1 mb-2">
        <span v-if="!isGeneric">Last seen: March 10, 2024 at 10:45 AM &bull; {{ device.location }}</span>
        <span v-else>Seen in {{ device.city }}</span>
      </div>
      <v-btn text color="primary" class="text-none" to="/explore">
        Show all history
        <v-icon right small>mdi-arrow-right</v-icon>
      </v-btn>
    </div>

    <v-divider class="mb-6"></v-divider>

    <!-- 4. Notes -->
    <div>
      <div class="overline mb-2">Notes</div>
      <v-textarea
        v-model="device.notes"
        :placeholder="isGeneric ? 'Add any personal notes about this record...' : 'Add any personal notes about this device...'"
        outlined
        dense
        background-color="white"
        rows="2"
        class="rounded-lg"
        hide-details
      ></v-textarea>
    </div>

    <!-- 5. Optional Help Footer -->
    <div v-if="isGeneric" class="mt-6 pt-4">
      <p class="body-2 grey--text text--darken-1 mb-0">
        <v-icon small color="grey" class="mr-1">mdi-information-outline</v-icon>
        To group this record, drag this card onto one of your confirmed devices above.
      </p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DeviceDetailDropdown',
  props: {
    device: {
      type: Object,
      required: true
    },
    isGeneric: {
      type: Boolean,
      default: false
    }
  }
}
</script>
