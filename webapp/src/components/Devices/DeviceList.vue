<template>
  <div class="ts-device-list">
    <div class="py-8"></div>
    <!-- Rename Device Dialog -->
    <v-dialog v-model="renameDeviceDialog" width="600">
      <v-card class="pa-4">
        <RenameDevice 
          :device="deviceToRename"
          @device-labeled="handleDeviceLabeled"
          @close="renameDeviceDialog = false"
        ></RenameDevice>
      </v-card>
    </v-dialog>

    <!-- Merge Modal -->
    <DeviceMergeModal
      :device="mergeContext.device"
      :show-merge="showMergeDialog"
      :show-preview="showPreviewDialog"
      :selected-variants="mergeContext.selectedVariants"
      :new-label="mergeContext.newLabel"
      @update-dialog="handleDialogUpdate"
      @update-selected-variants="handleSelectVariants"
      @update-label="mergeContext.newLabel = $event"
      @preview="previewMerge"
      @confirm-merge="confirmMerge"
      @close-merge="showMergeDialog = false"
      @close-preview="showPreviewDialog = false"
    />

    <!-- Device Table (styled like EventList) -->
    <v-data-table
      :headers="headers"
      :items="devices"
      item-key="id"
      disable-pagination
      hide-default-footer
      flat
    >
      <!-- <template v-slot:top>
        <v-toolbar dense flat color="transparent" class="mb-2">
          <span style="display: inline-block; min-width: 200px">
            <small>{{ devices.length }} trusted devices</small>
          </span>
          <v-spacer></v-spacer>
        </v-toolbar>
      </template> -->

      <!-- Device Row -->
      <template v-slot:item="{ item }">
        <tr 
          class="device-row"
          :class="{ 'device-row-expanded': expandedDeviceIds[item.id] }"
          @click="toggleExpanded(item.id)"
        >
          <!-- Expand Arrow -->
          <!-- <td style="text-align: center;">
            <v-icon medium>{{ expandedDeviceIds[item.id] ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
          </td> -->

          <!-- Actions -->
          <td style="text-align: center;">
            <v-btn small icon @click.stop="item.starred = !item.starred">
              <v-icon title="Toggle star status" v-if="item.starred" color="amber">mdi-star</v-icon>
              <v-icon title="Toggle star status" v-else>mdi-star-outline</v-icon>
            </v-btn>
            <v-btn small icon @click.stop="item.tagged = !item.tagged" class="ml-1">
              <v-icon title="Modify tags" v-if="item.tagged">mdi-tag-plus</v-icon>
              <v-icon title="Modify tags" v-else>mdi-tag-plus-outline</v-icon>
            </v-btn>
          </td>

          <!-- Device Icon -->
          <td style="text-align: center;">
            <v-icon size="64">{{ getDeviceIcon(item.model) }}</v-icon>
          </td>

          <!-- Device Model -->
          <td style="font-weight: 500;">
            <span class="font-weight-600">{{ item.model }}</span>
          </td>

          <!-- Label -->
          <td class="device-label-cell">
            <v-hover v-slot="{ hover }">
              <div class="label-container">
                <span 
                  v-if="item.label" 
                  class="text-body-2"
                >
                  {{ item.label }}
                </span>
                <span 
                  v-else 
                  class="text-body-2 grey--text text--darken-2"
                  style="font-style: italic;"
                >
                  Label this device
                </span>
                <v-icon 
                  v-if="hover"
                  small 
                  class="ml-2 label-icon"
                  @click.stop="openRenameDialog(item)"
                >
                  mdi-pencil
                </v-icon>
              </div>
            </v-hover>
          </td>

          <!-- Platforms + Last Seen -->
          <!-- <td class="device-platforms-cell"> -->
            <td><PlatformGrid /></td>

          <!-- Event Count -->
          <!-- <td style="text-align: right; color: #666;"> -->
          <!-- <td style="text-align: center; color: #666;">
            <span class="text-body-2">{{ item.eventCount }} events</span>
          </td> -->

          <!-- Variants Indicator -->
          <!-- <td v-if="item.variants && item.variants.length > 1" style="display: flex; justify-content: flex-end; align-items: center; width: 100%;"> -->
            <td v-if="item.variants && item.variants.length > 1" style="text-align: right;">
            <v-chip outlined color="info" class="d-flex align-center" style="white-space: normal; max-width: 150px; height: auto; padding: 12px; margin-left: auto;">
              <v-icon small left>mdi-information-outline</v-icon>
              <span class="text-caption pl-2">Multiple records</span>
            </v-chip>
          </td>
          <td v-else></td>
        </tr>

        <!-- Expanded Content Row -->
        <tr v-show="expandedDeviceIds[item.id]" class="device-detail-row">
          <td colspan="7" class="pa-0">
            <DebugDeviceDetail
              :device="item"
              :expanded-platforms="expandedPlatforms"
              @update-label="item.label = $event"
              @toggle-platform="togglePlatformExpanded"
              @open-merge="openMergeDialog"
              @unmerge="unmerge"
              @add-comment="addComment"
              @delete-comment="deleteComment"
              @update-comment-text="updateCommentText"
            />
          </td>
        </tr>
      </template>
    </v-data-table>
  </div>
</template>

<script>
import DeviceMergeModal from './DeviceMergeModal.vue'
import DebugDeviceDetail from './DebugDeviceDetail.vue'
import PlatformGrid from './PlatformGrid.vue'
import RenameDevice from './RenameDevice.vue'

export default {
  name: 'DeviceList',
  components: {
    DeviceMergeModal,
    DebugDeviceDetail,
    PlatformGrid,
    RenameDevice,
  },
  data() {
    return {
      expandedDeviceIds: {},
      expandedPlatforms: {},
      editingDeviceId: null,
      showMergeDialog: false,
      showPreviewDialog: false,
      renameDeviceDialog: false,
      deviceToRename: {},
      headers: [
        // { text: '', align: 'center', sortable: false, value: 'expand', width: '50' },
        { text: '', align: 'center', sortable: false, value: 'actions', width: '100' },
        { text: '', align: 'center', sortable: false, value: 'icon', width: '80' },
        { text: 'Device', align: 'left', sortable: false, value: 'model', width: '150' },
        { text: ' ', align: 'start', sortable: false, value: 'label', width: '200' },
        { text: 'Platforms', align: 'left', sortable: false, value: 'platforms', width: 'auto' },
        { text: '', align: 'end', sortable: false, value: 'warning', width: '180' },
      ],
      mergeContext: {
        device: {},
        variants: [],
        selectedVariants: [],
        newLabel: '',
      },
      devices: [
        {
          id: 1,
          model: 'iPhone 15 Pro',
          label: '',
          firstSeen: 'Dec 2, 2025',
          lastSeen: 'Jan 18, 2026',
          eventCount: 1247,
          isMerged: false,
          starred: false,
          tagged: false,
          variants: [
            { id: 'ABC123', platform: 'Facebook', ip: '192.168.1.100', appInfo: 'Facebook for iOS', model: 'iPhone 15 Pro', isPrimary: true, lastSeen: 'Jan 18, 2026' },
            { id: 'ABC123_safari', platform: 'Facebook', ip: '192.168.1.100', appInfo: 'Safari', model: 'iPhone 15 Pro', isPrimary: false, lastSeen: 'Jan 18, 2026' },
          ],
          platforms: [
            {
              name: 'Facebook',
              active: true,
              firstSeen: 'Dec 5, 2025',
              lastSeen: 'Jan 18, 2026 2:14 PM',
              ip: '192.168.1.100',
              userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X)',
            },
            {
              name: 'Instagram',
              active: false,
              firstSeen: 'Dec 10, 2025',
              lastSeen: 'Jan 5, 2026 11:45 AM',
              ip: '192.168.1.100',
              userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)',
            },
            {
              name: 'Gmail',
              active: true,
              firstSeen: 'Nov 28, 2025',
              lastSeen: 'Jan 20, 2026 9:32 PM',
              ip: '192.168.1.105',
              userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X)',
            },
          ],
          comments: [
            { id: 1, content: 'this phone is always with me', created_at: 1769063901000 },
          ],
        },
        {
          id: 2,
          model: 'MacBook Pro 16-inch',
          label: '',
          firstSeen: 'Sep 15, 2025',
          lastSeen: 'Jan 21, 2026',
          eventCount: 3891,
          isMerged: true,
          starred: false,
          tagged: false,
          variants: [
            { id: 'XYZ789', isPrimary: true, lastSeen: 'Jan 21, 2026' },
            { id: 'XYZ789_v2', isPrimary: false, lastSeen: 'Jan 19, 2026' }
          ],
          platforms: [
            {
              name: 'Apple',
              active: true,
              firstSeen: 'Sep 15, 2025',
              lastSeen: 'Jan 21, 2026 3:45 PM',
              ip: '10.0.0.50',
              userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            },
            {
              name: 'Gmail',
              active: true,
              firstSeen: 'Sep 20, 2025',
              lastSeen: 'Jan 21, 2026 4:12 PM',
              ip: '10.0.0.50',
              userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            },
            {
              name: 'Discord',
              active: false,
              firstSeen: 'Oct 1, 2025',
              lastSeen: 'Jan 10, 2026 8:22 PM',
              ip: '10.0.0.51',
              userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            },
          ],
          comments: [
            { id: 1, content: 'Work laptop used for development', created_at: 1705516800000 },
          ],
        },
      ],
    }
  },
  methods: {
    getDeviceIcon(model) {
      const modelLower = model.toLowerCase()
      if (modelLower.includes('iphone')) return 'mdi-cellphone'
      if (modelLower.includes('ipad')) return 'mdi-tablet'
      if (modelLower.includes('macbook') || modelLower.includes('mac mini') || modelLower.includes('mac studio')) return 'mdi-laptop'
      if (modelLower.includes('windows') || modelLower.includes('pc')) return 'mdi-laptop-windows'
      if (modelLower.includes('android')) return 'mdi-android'
      if (modelLower.includes('watch')) return 'mdi-watch'
      return 'mdi-devices' // fallback generic device icon
    },
    getLastSeenTime(device) {
      if (!device.platforms || device.platforms.length === 0) return ''
      
      // Find the most recent lastSeen time across all active platforms
      let mostRecent = null
      device.platforms.forEach(platform => {
        if (platform.active && platform.lastSeen) {
          if (!mostRecent) {
            mostRecent = new Date(platform.lastSeen)
          } else {
            const platformDate = new Date(platform.lastSeen)
            if (platformDate > mostRecent) {
              mostRecent = platformDate
            }
          }
        }
      })
      
      if (!mostRecent) return ''
      
      // Format as short date/time
      return mostRecent.toLocaleDateString() + ' ' + mostRecent.toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    },
    toggleExpanded(deviceId) {
      this.$set(this.expandedDeviceIds, deviceId, !this.expandedDeviceIds[deviceId])
    },
    toggleDetailedDevice(device) {
      this.$set(this.expandedDeviceIds, device.id, !this.expandedDeviceIds[device.id])
    },
    togglePlatformExpanded(deviceId, platformName) {
      const key = `${deviceId}-${platformName}`
      this.$set(this.expandedPlatforms, key, !this.expandedPlatforms[key])
    },
    handleDialogUpdate(dialogType, isOpen) {
      if (dialogType === 'merge') {
        this.showMergeDialog = isOpen
      } else if (dialogType === 'preview') {
        this.showPreviewDialog = isOpen
      }
    },
    handleSelectVariants(selectedIds) {
      this.mergeContext.selectedVariants = selectedIds
    },
    openMergeDialog(device) {
      this.mergeContext.device = device
      this.mergeContext.variants = [...device.variants]
      this.mergeContext.selectedVariants = device.variants.slice(1).map(v => v.id)
      this.mergeContext.newLabel = device.label
      this.showMergeDialog = true
    },
    previewMerge() {
      this.showMergeDialog = false
      this.showPreviewDialog = true
    },
    confirmMerge() {
      if (this.mergeContext.newLabel) {
        this.mergeContext.device.label = this.mergeContext.newLabel
      }
      this.mergeContext.device.isMerged = true
      this.showPreviewDialog = false
      this.showMergeDialog = false
    },
    unmerge(device) {
      device.isMerged = false
    },
    addComment(device) {
      if (device.newComment && device.newComment.trim()) {
        if (!device.comments) {
          device.comments = []
        }
        device.comments.push({
          id: Date.now(),
          content: device.newComment,
          created_at: Date.now(),
        })
        device.newComment = ''
      }
    },
    deleteComment({ deviceId, index }) {
      const device = this.devices.find(d => d.id === deviceId)
      if (device && device.comments) {
        device.comments.splice(index, 1)
      }
    },
    updateCommentText({ deviceId, text }) {
      const device = this.devices.find(d => d.id === deviceId)
      if (device) {
        device.newComment = text
      }
    },
    openRenameDialog(device) {
      this.deviceToRename = device
      this.renameDeviceDialog = true
    },
    handleDeviceLabeled({ deviceId, label }) {
      const device = this.devices.find(d => d.id === deviceId)
      if (device) {
        device.label = label
      }
    },
  },
  filters: {
    shortDateTime(timestamp) {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    },
  },
}
</script>

<style scoped lang="scss">
.ts-device-list {
  width: 100%;
  background-color: transparent;

  .label-container {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 8px;
    
    &:hover .label-icon {
      opacity: 1;
    }
  }

  .label-icon {
    opacity: 0;
    transition: opacity 0.2s ease;
    cursor: pointer;
    flex-shrink: 0;

    &:hover {
      opacity: 0.8;
    }
  }

  .device-row {
    cursor: pointer;
    // height: 200px;
    transition: background-color 0.2s ease;

    &:hover {
      background-color: #f5f5f5;
    }

    &-expanded {
      background-color: #fafafa;
    }
  }

  .device-detail-row {
    border-top: 2px solid #e8e8e8;

    &:hover {
      background-color: transparent !important;
    }

    td {
      padding: 0 !important;
      border-bottom: none;
      vertical-align: top;
    }
  }

//   .device-platforms-cell {
//     flex: 1;
//     min-width: 280px;
//     padding: 0 !important;
//     margin: 0 !important;
//   }

  ::v-deep .v-data-table {
    background-color: transparent;
    table-layout: fixed;

    td {
      padding: 20px 10px !important;
      border-bottom: 1px solid #e8e8e8;
      height: auto;
      vertical-align: middle;
    }

    td:last-child {
      padding-right: 10px !important;
    }

    td:first-child {
      padding-left: 10px !important;
    }
  }

  ::v-deep .device-detail-row td {
    padding: 0 !important;
  }
}
</style>
