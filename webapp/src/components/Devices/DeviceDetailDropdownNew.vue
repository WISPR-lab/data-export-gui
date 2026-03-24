<template>
  <div class="pa-6">
    <!-- 1. Custom Name (Only for confirmed devices) -->
    <div v-if="!isGeneric" class="mb-6">
      <v-text-field
        v-model="device.user_label"
        placeholder="Give this device a name (e.g. Work Phone)"
        outlined
        dense
        prepend-inner-icon="mdi-pencil"
        class="rounded-lg"
        hide-details
        style="max-width: 500px;"
        @change="$emit('change')"
      ></v-text-field>
    </div>

    <v-divider v-if="!isGeneric" class="mb-6"></v-divider>

    <!-- 2. Device Attributes Grid -->
    <div v-if="filteredAttributes.length > 0" class="mb-6">
      <div class="overline mb-3">Device details</div>
      <v-simple-table dense>
        <template v-slot:default>
          <tbody>
            <tr v-for="(value, key) in deviceAttributesObject" :key="key">
              <td style="font-weight: 500; max-width: 200px;">{{ key }}</td>
              <td style="word-break: break-word;">{{ formatAttributeValue(value) }}</td>
            </tr>
          </tbody>
        </template>
      </v-simple-table>
    </div>

    <v-divider class="mb-6"></v-divider>

    <!-- 3. Notes -->
    <div>
      <div class="overline mb-2">Notes</div>
      <v-textarea
        v-model="device.notes"
        :placeholder="isGeneric ? 'Add any personal notes about this record...' : 'Add any personal notes about this device...'"
        outlined
        dense
        rows="2"
        class="rounded-lg"
        hide-details
        @change="$emit('change')"
      ></v-textarea>
    </div>

    <!-- 4. Optional Help Footer for Generic Records -->
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
  name: 'DeviceDetailDropdownNew',
  props: {
    device: {
      type: Object,
      required: true
    },
    isGeneric: {
      type: Boolean,
      default: false
    }
  },
  computed: {
    deviceAttributesObject() {
      // Parse and display device attributes from the attributes JSON field
      if (!this.device.attributes) return {}
      
      try {
        if (typeof this.device.attributes === 'string') {
          return JSON.parse(this.device.attributes)
        }
        return this.device.attributes
      } catch (e) {
        console.warn('Failed to parse device attributes:', e)
        return {}
      }
    },
    filteredAttributes() {
      return Object.entries(this.deviceAttributesObject)
    }
  },
  methods: {
    formatAttributeValue(value) {
      if (typeof value === 'boolean') {
        return value ? 'Yes' : 'No'
      }
      if (typeof value === 'object') {
        return JSON.stringify(value)
      }
      return String(value)
    }
  }
}
</script>

<style scoped>
/* Optional styling */
</style>
