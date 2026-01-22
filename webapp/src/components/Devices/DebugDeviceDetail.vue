<template>
  <div>
    <v-row>
      <v-col cols="12">
        <v-card flat style="background-color: transparent">
          <v-row style="height: 100%; margin: 0;">
            <v-col cols="8" style="padding: 0;">
              <v-card-text v-if="device.variants && device.variants.length > 1" class="pa-0" style="background-color: transparent;">
        <div class="d-flex align-center mb-3 px-4 pt-4">
          <v-icon small color="info" class="mr-2">mdi-information-outline</v-icon>
          <span class="text-subtitle-2 font-weight-500">Linked Records</span>
        </div>
        
        <p class="text-caption mb-4 px-4" style="color: #666;">
          These records are grouped as one device. If they're actually different devices, you can separate them below.
        </p>
        
        <div class="px-4">
          <!-- Timeline 0 Variant -->
          <div v-if="device.variants && device.variants[0]" class="record-item">
            <ts-timeline-component
              :timeline="$store.state.sketch.timelines[0]"
              :is-selected="false"
            >
              <template v-slot:processed="slotProps">
                <div :style="{ backgroundColor: $vuetify.theme.dark ? '#303030' : '#f5f5f5', display: 'flex', alignItems: 'center', gap: '12px', width: 'fit-content', padding: '4px 12px', borderRadius: '16px' }">
                  <v-icon :color="slotProps.timelineChipColor" size="20">mdi-circle</v-icon>
                  <span class="text-body-2">{{ $store.state.sketch.timelines[0].name }}</span>
                </div>
              </template>
            </ts-timeline-component>
            <v-card outlined>
              <v-simple-table dense style="table-layout: fixed; width: 100%;">
                <template v-slot:default>
                  <tbody>
                    <tr>
                      <td style="width: 300px;">IP</td>
                      <td>{{ device.variants[0].ip || '—' }}</td>
                    </tr>
                    <tr>
                      <td>App</td>
                      <td>{{ device.variants[0].appInfo || '—' }}</td>
                    </tr>
                    <tr>
                      <td>Model</td>
                      <td>{{ device.variants[0].model || '—' }}</td>
                    </tr>
                  </tbody>
                </template>
              </v-simple-table>
            </v-card>
            <!-- COMMENTED OUT OLD CODE:
            <div class="field-row">
              <span class="field-label">IP:</span>
              <span class="field-value">{{ device.variants[0].ip || '—' }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">App:</span>
              <span class="field-value">{{ device.variants[0].appInfo || '—' }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">Model:</span>
              <span class="field-value">{{ device.variants[0].model || '—' }}</span>
            </div>
            -->
          </div>

          <!-- Timeline 1 Variant -->
          <div v-if="device.variants && device.variants[1]" class="record-item">
            <ts-timeline-component
              :timeline="$store.state.sketch.timelines[0]"
              :is-selected="false"
            >
              <template v-slot:processed="slotProps">
                <div :style="{ backgroundColor: $vuetify.theme.dark ? '#303030' : '#f5f5f5', display: 'flex', alignItems: 'center', gap: '12px', width: 'fit-content', padding: '4px 12px', borderRadius: '16px' }">
                  <v-icon :color="slotProps.timelineChipColor" size="20">mdi-circle</v-icon>
                  <span class="text-body-2">{{ $store.state.sketch.timelines[0].name }}</span>
                </div>
              </template>
            </ts-timeline-component>
            <v-card outlined>
              <v-simple-table dense style="table-layout: fixed; width: 100%;">
                <template v-slot:default>
                  <tbody>
                    <tr>
                      <td style="width: 300px;">IP</td>
                      <td>{{ device.variants[1].ip || '—' }}</td>
                    </tr>
                    <tr>
                      <td>App</td>
                      <td>{{ device.variants[1].appInfo || '—' }}</td>
                    </tr>
                    <tr>
                      <td>Model</td>
                      <td>{{ device.variants[1].model || '—' }}</td>
                    </tr>
                  </tbody>
                </template>
              </v-simple-table>
            </v-card>
            <!-- COMMENTED OUT OLD CODE:
            <div class="field-row">
              <span class="field-label">IP:</span>
              <span class="field-value">{{ device.variants[1].ip || '—' }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">App:</span>
              <span class="field-value">{{ device.variants[1].appInfo || '—' }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">Model:</span>
              <span class="field-value">{{ device.variants[1].model || '—' }}</span>
            </div>
            -->
          </div>
        </div>

        <v-card-actions class="pa-4 pt-4">
          <v-btn 
            small 
            text
            @click="$emit('unmerge', device)"
          >
            <v-icon small left>mdi-undo</v-icon>
            Separate Records into Distinct Devices
          </v-btn>
        </v-card-actions>
      </v-card-text>
            </v-col>
            <!-- <v-col cols="4" style="border-left: 1px solid #e8e8e8; padding: 0;"> -->
              <v-col cols="4">
              <!-- Comments Section -->
              <DeviceComments
                :device="device"
                @add-comment="$emit('add-comment', $event)"
                @delete-comment="$emit('delete-comment', $event)"
              />
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>
    <div class="py-4"></div>
  </div>
</template>

<script>
import DeviceComments from './DeviceComments.vue'
import TsTimelineComponent from '../Explore/TimelineComponent.vue';
import { divide } from 'lodash';

export default {
  name: 'DebugDeviceDetail',
  components: {
    TsTimelineComponent,
    DeviceComments,
  },
  props: {
    device: {
      type: Object,
      required: true,
    },
    expandedPlatforms: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
    }
  },
  methods: {
  },
}
</script>

<style scoped lang="scss">
.record-item {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 16px;
  margin-bottom: 24px;
  align-items: start;
}


.record-divider {
  display: none;
}

// ::v-deep .v-simple-table {

// }

// ::v-deep .v-simple-table td:first-child {
//   width: 300px !important;
// }

// ::v-deep .v-simple-table td:first-child {
//   width: 300px !important;
// }
</style>