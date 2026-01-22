<template>
  <div>
    <!-- Merge Modal -->
    <v-dialog v-model="showMergeDialog" max-width="600px" @input="$emit('update-dialog', 'merge', $event)">
      <v-card class="pa-6" v-if="device && device.id">
        <h3>Consolidate Device Variants</h3>
        <p class="mt-2 text-caption" style="color: #666">
          Merge similar device IDs into a single device record
        </p>

        <v-divider class="my-4"></v-divider>

        <div class="mb-4">
          <p class="text-caption font-weight-500">Merging into:</p>
          <p class="ml-2">
            <strong>{{ device.label || device.model }}</strong>
            ({{ device.model }})
          </p>
        </div>

        <div class="mb-4">
          <p class="text-caption font-weight-500">Select variants to merge:</p>
          <v-list dense>
            <v-list-item v-for="variant in device.variants" :key="variant.id">
              <v-list-item-action>
                <v-checkbox
                  :value="variant.id"
                  :input-value="selectedVariants"
                  @change="$emit('update-selected-variants', $event)"
                ></v-checkbox>
              </v-list-item-action>
              <v-list-item-content>
                <v-list-item-title class="text-body2">
                  {{ variant.id }}
                  <span v-if="variant.isPrimary" class="text-caption" style="color: #2196f3">(Primary)</span>
                </v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  Last seen: {{ variant.lastSeen }}
                </v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>
          </v-list>
        </div>

        <div class="mb-6">
          <p class="text-caption font-weight-500">Keep label as:</p>
          <v-text-field
            :value="newLabel"
            dense
            outlined
            placeholder="Device label"
            class="mt-2"
            @input="$emit('update-label', $event)"
          ></v-text-field>
        </div>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="$emit('close-merge')">Cancel</v-btn>
          <v-btn text color="primary" @click="$emit('preview')">Preview</v-btn>
          <v-btn color="primary" @click="$emit('confirm-merge')">Merge</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Preview Modal -->
    <v-dialog v-model="showPreviewDialog" max-width="500px" @input="$emit('update-dialog', 'preview', $event)">
      <v-card class="pa-6" v-if="device && device.id">
        <h3>Merge Preview</h3>
        <v-divider class="my-4"></v-divider>

        <v-list dense>
          <v-list-item>
            <v-list-item-content>
              <v-list-item-subtitle>Variants being merged</v-list-item-subtitle>
              <p class="mt-2">{{ selectedVariants.length }} device ID(s)</p>
            </v-list-item-content>
          </v-list-item>
          <v-divider></v-divider>
          <v-list-item>
            <v-list-item-content>
              <v-list-item-subtitle>Combined event count</v-list-item-subtitle>
              <p class="mt-2">{{ device.eventCount }} events</p>
            </v-list-item-content>
          </v-list-item>
          <v-divider></v-divider>
          <v-list-item>
            <v-list-item-content>
              <v-list-item-subtitle>New label</v-list-item-subtitle>
              <p class="mt-2">{{ newLabel || device.label }}</p>
            </v-list-item-content>
          </v-list-item>
        </v-list>

        <v-card-actions class="mt-4">
          <v-spacer></v-spacer>
          <v-btn text @click="$emit('close-preview')">Back</v-btn>
          <v-btn color="primary" @click="$emit('confirm-merge')">Confirm Merge</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
export default {
  name: 'DeviceMergeModal',
  props: {
    device: {
      type: Object,
      default: () => ({}),
    },
    showMerge: {
      type: Boolean,
      default: false,
    },
    showPreview: {
      type: Boolean,
      default: false,
    },
    selectedVariants: {
      type: Array,
      default: () => [],
    },
    newLabel: {
      type: String,
      default: '',
    },
  },
  computed: {
    showMergeDialog: {
      get() {
        return this.showMerge
      },
      set(val) {
        this.$emit('update-dialog', 'merge', val)
      },
    },
    showPreviewDialog: {
      get() {
        return this.showPreview
      },
      set(val) {
        this.$emit('update-dialog', 'preview', val)
      },
    },
  },
  emits: [
    'update-dialog',
    'update-selected-variants',
    'update-label',
    'preview',
    'confirm-merge',
    'close-merge',
    'close-preview',
  ],
}
</script>
