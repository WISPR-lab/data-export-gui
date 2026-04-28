<template>
  <div class="pa-6">
    <div class="d-flex mb-6" style="gap: 36px;">
      <div style="flex: 0 0 auto; width: 300px;">
        <div class="overline">Name</div>
        
        <div class="mb-8">
          <v-text-field
            v-model="device.user_label"
            placeholder="e.g. Work Phone"
            outlined
            dense
            class="rounded-lg"
            hide-details
            @change="$emit('change')"
          ></v-text-field>
        </div> <!-- prepend-inner-icon="mdi-pencil" -->

<!--         
        <div class="mb-8">
          <div class="overline mb-2">Tags</div>
          <v-icon 
            small 
            class="cursor-pointer mb-2" 
            title="Add tag"
            @click="showTagDialog = true"
          >
            mdi-tag-plus-outline
          </v-icon>
          <div class="d-flex flex-wrap align-center" style="gap: 4px;">
            <v-chip
              v-for="tag in device.tags || []"
              :key="tag"
              small
              close
              @click:close="removeTag(tag)"
            >
              {{ tag }}
            </v-chip>
          </div>
        </div>

        Tag Dialog
        <v-dialog v-model="showTagDialog" max-width="400">
          <v-card>
            <v-card-title>Add Tag</v-card-title>
            <v-card-text>
              <v-combobox
                ref="tagInput"
                v-model="newTag"
                :items="availableTags"
                label="Tag name"
                outlined
                dense
                hide-details
                @keydown.enter="addTag"
              ></v-combobox>
            </v-card-text>
            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn text @click="showTagDialog = false">Cancel</v-btn>
              <v-btn text color="primary" @click="addTag">Add</v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog> -->
      </div>

      <!-- Right Column: Notes (tall, expands) -->
      <div style="flex: 1 0 auto;">
        <div class="overline">Notes</div>
        <v-textarea
          v-model="device.notes"
          :placeholder="isGeneric ? 'Add any personal notes about this record.' : 'Add any personal notes about this device.'"
          outlined
          dense
          rows="1"
          class="rounded-lg"
          hide-details
          @change="$emit('change')"
        ></v-textarea>
      </div>
    </div>

    <v-divider class="mb-6"></v-divider>

    <!-- 2. Device Records (Atomics) -->
    <div v-if="device.atomicDevices && device.atomicDevices.length > 0" class="mb-6 grey--lighten-5">
      <div class="overline mb-3">Device Records ({{ device.atomicDevices.length }})</div>
      <div class="space-y-2" style="display: flex; flex-direction: column; gap: 12px;">
        <AtomicDeviceRecord
          v-for="atomic in device.atomicDevices"
          :key="atomic.id"
          :atomic="atomic"
          @showJSON="$emit('showJSON', $event)"
          @unmerge="$emit('unmerge', $event)"
        />
      </div>
    </div>

    <!-- <v-divider v-if="device.atomicDevices && device.atomicDevices.length > 0" class="mb-6"></v-divider> -->

    <!-- 3. Device Attributes Grid -->
    <!-- <div v-if="filteredAttributes.length > 0" class="mb-6">
      <div class="overline mb-3">Device details</div>
      <v-simple-table dense class="grey lighten-5">
        <template v-slot:default>
          <tbody>
            <tr v-for="(value, key) in deviceAttributesObject" :key="key">
              <td style="font-weight: 500; min-width: 280px;">{{ key }}</td>
              <td style="word-break: break-word;">{{ formatAttributeValue(value) }}</td>
            </tr>
          </tbody>
        </template>
      </v-simple-table>
    </div> -->

    

    <!-- Optional Help Footer for Generic Records -->
    <div v-if="isGeneric" class="mt-6 pt-4">
      <p class="body-2 grey--text text--darken-3 mb-0">
        <v-icon small class="mr-1" color="grey--darken-3">mdi-information-outline</v-icon>
        To group this record, drag this card onto one of your confirmed devices above.
      </p>
    </div>
  </div>
</template>

<script>
import OriginChip from './OriginChip.vue';
import AtomicDeviceRecord from './AtomicDeviceRecord.vue';

export default {
  name: 'DeviceDetailDropdown',
  components: {
    OriginChip,
    AtomicDeviceRecord
  },
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
  data() {
    return {
      showTagDialog: false,
      newTag: null
    }
  },
  computed: {
    availableTags() {
      if (!this.device.tags) return []
      return this.device.tags
    },
    deviceAttributesObject() {
      if (!this.device.attributes) return {}
      
      try {
        let attrs = {}
        const parsed = typeof this.device.attributes === 'string'
          ? JSON.parse(this.device.attributes)
          : this.device.attributes
        
        for (const [key, value] of Object.entries(parsed)) {
          if (value !== null && value !== undefined && value !== '') {
            attrs[key] = value
          }
        }
        return attrs
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
    },
    removeTag(tag) {
      if (!this.device.tags) return
      const index = this.device.tags.indexOf(tag)
      if (index > -1) {
        this.device.tags.splice(index, 1)
        this.$emit('change')
      }
    },
    addTag() {
      if (!this.newTag || this.newTag.trim() === '') return
      if (!this.device.tags) {
        this.$set(this.device, 'tags', [])
      }
      const tag = this.newTag.trim()
      if (!this.device.tags.includes(tag)) {
        this.device.tags.push(tag)
        this.$emit('change')
      }
      this.newTag = null
      this.showTagDialog = false
    }
  }
}
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
</style>

