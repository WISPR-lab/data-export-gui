<template>
  <div class="pa-6">
    <!-- 1. Custom Name -->
    <div class="mb-6">
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

    <v-divider class="mb-6"></v-divider>

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
        placeholder="Add any personal notes about this device..."
        outlined
        dense
        rows="2"
        class="rounded-lg"
        hide-details
        @change="$emit('change')"
      ></v-textarea>
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
