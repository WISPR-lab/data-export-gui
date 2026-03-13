<template>
  <v-container class="pa-6 white min-h-100" style="max-width: 900px;">
    <div class="mb-8">
      <h1 class="text-h4 font-weight-bold mb-2">Your devices</h1>
      <p class="body-1 grey--text text--darken-2">
        We found activity from these devices in your data export(s). You can label devices as malicious or give them custom names to keep track of them.
      </p>
    </div>


    <v-expansion-panels flat class="device-panels">
      <v-expansion-panel
        v-for="(dev, i) in devices"
        :key="i"
        class="mb-3 border rounded-xl overflow-hidden device-drop-zone"
        :class="{'drop-active': isDragging && activeDropId === i}"
        @dragover.native.prevent="activeDropId = i"
        @dragleave.native="activeDropId = null"
        @drop.native="onDrop($event, dev, i)"
      >
        <v-expansion-panel-header class="pa-4">
          <template v-slot:default="{ open }">
            <device-header :device="dev" :open="open" />
          </template>
        </v-expansion-panel-header>

        <v-expansion-panel-content class="grey lighten-5 border-top">
          <device-detail-dropdown :device="dev" />
        </v-expansion-panel-content>
      </v-expansion-panel>
    </v-expansion-panels>


    <div v-if="unassigned.length > 0" class="mt-12 mb-10">
      <div class="mb-6">
        <h2 class="text-h6 font-weight-bold grey--text text--darken-4 mb-2">Sessions to Review</h2>
        <div class="body-1 grey--text text--darken-2">
            <p class="mb-1">These sessions are missing some specific device details. This usually happens when you use a web browser or private mode.</p>
            <p>They might belong to one of your devices above, or several of these records might actually be the same device.
            <!-- We couldn't automatically match these to specific device. This often happens when using private browsing mode or a different browser on your existing devices.  -->
            If you recognize them, <span class="font-weight-bold">drag and drop</span> them onto the correct profile above.</p>
        </div>
      </div>

      <v-expansion-panels flat class="device-panels">
        <v-expansion-panel
          v-for="(item, i) in unassigned"
          :key="i"
          class="mb-3 border rounded-xl overflow-hidden blue-grey lighten-5"
          draggable
          @dragstart.native="onDragStart($event, item)"
          @dragend.native="onDragEnd"
        >
          <v-expansion-panel-header class="pa-4">
            <template v-slot:default="{ open }">
              <device-header :device="item" is-generic :open="open" />
            </template>
          </v-expansion-panel-header>

          <v-expansion-panel-content class="grey lighten-5 border-top">
            <device-detail-dropdown :device="item" is-generic />
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </div>


    <device-group-modal 
      v-model="groupDialog" 
      :source="staging ? staging.source : null" 
      :target="staging ? staging.target : null"
      @confirm="confirmGroup"
    />

  </v-container>
</template>

<script>
import DeviceDetailDropdown from '@/components/Devices/DeviceDetailDropdown.vue';
import DeviceHeader from '@/components/Devices/DeviceHeader.vue';
import DeviceGroupModal from '@/components/Devices/DeviceGroupModal.vue';

export default {
  name: 'DeviceMockup4',
  components: {
    DeviceDetailDropdown,
    DeviceHeader,
    DeviceGroupModal
  },
  data() {
    return {
      isDragging: false,
      activeDropId: null,
      groupDialog: false,
      selectedRecord: null,
      staging: null,
      unassigned: [
        { label: 'iPhone (Generic)', manufacturer: 'Apple', os: 'iOS 15.7', city: 'Madison, WI', notes: '' },
        { label: 'iPhone (Generic)', manufacturer: 'Apple', os: 'iOS 17.7', city: 'Chicago, IL', notes: '' },
      ],
      devices: [
        {
          model: 'iPhone 7',
          customLabel: '',
          manufacturer: 'Apple',
          location: 'Madison, WI',
          icon: 'mdi-cellphone',
          status: 'Needs Review',
          recordCount: 12,
          osHistory: ['iOS 15.0', 'iOS 15.7'],
          notes: ''
        },
        {
          model: 'iPhone XR',
          customLabel: 'Mom\'s Phone',
          manufacturer: 'Apple',
          location: 'Chicago, IL',
          icon: 'mdi-cellphone',
          status: 'Done',
          recordCount: 45,
          osHistory: ['iOS 17.7.1'],
          notes: 'Given to cousin in 2024.'
        },
        {
          model: 'MacBook Pro 16"',
          customLabel: '',
          manufacturer: 'Apple',
          location: 'Madison, WI',
          icon: 'mdi-laptop',
          status: 'Done',
          recordCount: 8,
          osHistory: ['macOS 14.5'],
          notes: ''
        }
      ]
    };
  },
  methods: {
    onDragStart(event, item) {
      this.isDragging = true;
      this.selectedRecord = item;
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', JSON.stringify(item));
    },
    onDragEnd() {
      this.isDragging = false;
      this.activeDropId = null;
    },
    onDrop(event, targetDevice, index) {
      if (!this.selectedRecord) return;
      this.staging = { source: this.selectedRecord, target: targetDevice, index };
      this.groupDialog = true;
      this.activeDropId = null;
    },
    confirmGroup() {
      const idx = this.unassigned.indexOf(this.staging.source);
      if (idx > -1) this.unassigned.splice(idx, 1);
      this.staging.target.recordCount++;
      this.staging.target.status = 'Needs Review';
      this.groupDialog = false;
      this.staging = null;
      this.selectedRecord = null;
    },
    cancelGroup() {
      this.groupDialog = false;
      this.staging = null;
      this.selectedRecord = null;
    }
  }
};
</script>

<style scoped>
.min-h-100 { min-height: 100vh; }
.white { background-color: #ffffff !important; }
.border { border: 1px solid rgba(0,0,0,0.12) !important; }
.border-dark { border: 1px solid rgba(0,0,0,0.24) !important; }
.border-top { border-top: 1px solid rgba(0,0,0,0.12) !important; }
.border-bottom { border-bottom: 1px solid rgba(0,0,0,0.12) !important; }
.border-blue-grey { border: 1px solid #cfd8dc !important; }
.gap-3 { gap: 12px; }

.rounded-xl { border-radius: 12px !important; }

.unassigned-chip {
  min-width: 180px;
  flex-shrink: 0;
  cursor: grab;
}

.device-panels ::v-deep .v-expansion-panel-header--active {
  background-color: #f8f9fa;
}

.device-drop-zone {
  transition: border 0.1s ease;
}

.drop-active {
  border: 1px solid #1976d2 !important;
  background-color: #e3f2fd !important;
}

/* Remove default shadow for a cleaner look */
.v-expansion-panel::before {
  box-shadow: none !important;
}
</style>
