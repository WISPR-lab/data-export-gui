<template>
  <v-container fluid class="pa-0 h-100" style="background: white; border-top: 1px solid rgba(0,0,0,0.12)">
    <!-- Main Content Area (Matches Sketch Layout) -->
    <div class="d-flex flex-row w-100 h-100 overflow-hidden" style="min-height: 80vh;">
      
      <!-- List Sidebar (Now inside the view, looks like the Explore side panels) -->
      <div class="device-list-sidebar border-right d-flex flex-column">
        <v-toolbar flat dense class="border-bottom flex-shrink-0">
          <v-toolbar-title class="subtitle-2 font-weight-bold">Device Assets</v-toolbar-title>
          <v-spacer></v-spacer>
          <v-chip x-small color="primary" outlined>{{ devices.length }} Groups</v-chip>
        </v-toolbar>

        <v-list two-line class="pa-0 overflow-y-auto flex-grow-1">
          <v-list-item-group v-model="selectedIdx" mandatory color="primary">
            <v-list-item
              v-for="(dev, i) in devices"
              :key="i"
              class="border-bottom px-4"
              @click="selectedDevice = dev"
            >
              <v-list-item-avatar tile size="32" class="mr-3">
                <v-icon :color="dev.status === 'pending' ? 'amber' : 'blue'">
                  {{ dev.type === 'smartphone' ? 'mdi-cellphone' : 'mdi-laptop' }}
                </v-icon>
              </v-list-item-avatar>
              <v-list-item-content>
                <v-list-item-title class="body-2 font-weight-bold">{{ dev.model }}</v-list-item-title>
                <v-list-item-subtitle class="caption">
                  {{ dev.manufacturer }} &bull; {{ dev.lastGeo }}
                </v-list-item-subtitle>
              </v-list-item-content>
              <v-list-item-action v-if="dev.status === 'pending'">
                <v-icon x-small color="amber darken-3">mdi-alert-circle</v-icon>
              </v-list-item-action>
            </v-list-item>
          </v-list-item-group>
        </v-list>
      </div>

      <!-- Detail Area -->
      <div class="flex-grow-1 overflow-y-auto detail-container pa-6">
        <template v-if="selectedDevice">
          <!-- Identity Summary -->
          <div class="d-flex align-start mb-6">
            <v-avatar size="56" color="grey lighten-4" class="mr-4">
              <v-icon color="primary" size="28">
                {{ selectedDevice.type === 'smartphone' ? 'mdi-cellphone' : 'mdi-laptop' }}
              </v-icon>
            </v-avatar>
            <div class="flex-grow-1">
              <div class="d-flex align-center">
                <h2 class="text-h5 font-weight-bold mb-0 mr-3">{{ selectedDevice.model }}</h2>
                <v-chip v-if="selectedDevice.status === 'pending'" small color="amber lighten-4" class="amber--text text--darken-4 font-weight-bold" label>
                  <v-icon left x-small>mdi-clock-outline</v-icon> Needs Review
                </v-chip>
                <v-chip v-else small color="blue lighten-4" class="blue--text text--darken-4 font-weight-bold" label>
                  <v-icon left x-small>mdi-shield-check</v-icon> Verified
                </v-chip>
              </div>
              <div class="text-body-2 grey--text text--darken-1">
                {{ selectedDevice.manufacturer }} &bull; Active {{ selectedDevice.firstSeen }} — {{ selectedDevice.lastSeen }}
              </div>
            </div>
            <v-btn text color="primary" small class="text-none">
              <v-icon left small>mdi-merge</v-icon> Merge Into Group
            </v-btn>
          </div>

          <!-- Interaction Prompt -->
          <v-card v-if="selectedDevice.status === 'pending'" flat outlined class="mb-6 verification-card border-amber-light">
            <v-card-text class="pa-4">
              <div class="d-flex align-center mb-2">
                <v-icon color="amber darken-3" class="mr-2">mdi-help-circle-outline</v-icon>
                <span class="subtitle-2 font-weight-bold amber--text text--darken-4">Verify Auto-Grouped Records</span>
              </div>
              <p class="body-2 mb-4">
                We've automatically grouped event records based on the model name <strong>"{{ selectedDevice.model }}"</strong>.
                Is it possible you had more than one of these devices in your household?
              </p>
              <div class="d-flex align-center">
                <v-btn small color="success" depressed class="mr-2 text-none" @click="selectedDevice.status = 'verified'">
                  Yes, it's one device
                </v-btn>
                <v-btn small outlined color="error" class="text-none" @click="showSplitDialog = true">
                   No, split this group
                </v-btn>
              </div>
            </v-card-text>
          </v-card>

          <!-- Investigation Data -->
          <v-row>
            <v-col cols="12" md="8">
              <!-- Indicators -->
              <v-card outlined class="mb-4">
                <v-card-title class="overline py-2 px-4 grey lighten-5 border-bottom">Forensic Indicators</v-card-title>
                <v-divider></v-divider>
                <v-card-text class="pa-4">
                  <v-row dense>
                    <v-col cols="6">
                      <div class="caption grey--text text-uppercase mb-1">Primary OS</div>
                      <div class="body-2 font-weight-medium">{{ selectedDevice.os }}</div>
                    </v-col>
                    <v-col cols="6">
                      <div class="caption grey--text text-uppercase mb-1">Main Location</div>
                      <div class="body-2 font-weight-medium">{{ selectedDevice.lastGeo }}</div>
                    </v-col>
                  </v-row>
                  
                  <div class="mt-4">
                    <div class="caption grey--text text-uppercase mb-2">Software Timeline</div>
                    <div class="d-flex align-center flex-wrap">
                      <v-tooltip bottom v-for="(os, idx) in selectedDevice.osHistory" :key="idx">
                        <template v-slot:activator="{ on, attrs }">
                          <v-chip x-small v-bind="attrs" v-on="on" class="mr-2 mb-1" color="grey lighten-3">
                            {{ os.ver }}
                          </v-chip>
                        </template>
                        <span>Upgrade detected on {{ os.date }}</span>
                      </v-tooltip>
                    </div>
                  </div>
                </v-card-text>
              </v-card>

              <!-- Notes -->
              <v-card outlined>
                <v-card-title class="overline py-2 px-4 grey lighten-5 border-bottom">Forensic Notes</v-card-title>
                <v-divider></v-divider>
                <v-card-text class="pa-4">
                  <div v-for="(note, nIdx) in selectedDevice.notes" :key="nIdx" class="mb-3 pa-2 rounded grey lighten-4">
                    <div class="d-flex justify-space-between mb-1">
                      <span class="caption font-weight-bold secondary--text">Investigation Note</span>
                      <span class="caption grey--text">{{ note.date }}</span>
                    </div>
                    <div class="body-2">{{ note.text }}</div>
                  </div>
                  <v-textarea
                    v-model="newNote"
                    placeholder="Add a finding about this device..."
                    outlined
                    dense
                    rows="2"
                    hide-details
                    class="mt-3 caption"
                  ></v-textarea>
                  <div class="d-flex justify-end mt-2">
                    <v-btn small depressed color="primary" @click="addNote">Add Finding</v-btn>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>

            <v-col cols="12" md="4">
              <!-- Conflict Detection -->
              <v-card v-if="selectedDevice.status === 'pending'" outlined class="border-amber-light mb-4">
                <v-card-title class="overline py-2 px-4 amber lighten-5 amber--text text--darken-4 border-bottom-amber">Inconsistencies</v-card-title>
                <v-card-text class="pa-4">
                  <p class="caption">Potential evidence found suggesting multiple hardware units:</p>
                  <div v-for="(factor, fIdx) in selectedDevice.diffFactors" :key="fIdx" class="mb-3">
                    <div class="caption font-weight-bold mb-1">{{ factor.key }}</div>
                    <div class="d-flex gap-1">
                      <v-chip v-for="(val, vIdx) in factor.vals" :key="vIdx" x-small color="error" outlined>
                        {{ val }}
                      </v-chip>
                    </div>
                  </div>
                </v-card-text>
              </v-card>

              <!-- Technical Stats -->
              <v-card outlined>
                <v-card-title class="overline py-2 px-4 grey lighten-5 border-bottom">Raw Details</v-card-title>
                <v-card-text class="pa-0">
                  <pre class="raw-box pa-3 mb-0">{{ selectedDevice.allAttributes }}</pre>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </template>
        <div v-else class="h-100 d-flex flex-column align-center justify-center grey--text">
          <v-icon size="48" color="grey lighten-3">mdi-cellphone-link</v-icon>
          <div class="body-2 mt-2">Select an asset group to start investigation</div>
        </div>
      </div>
    </div>

    <!-- UI Modal Mock -->
    <v-dialog v-model="showSplitDialog" max-width="800">
      <v-card>
        <v-card-title class="headline">Split Group records</v-card-title>
        <v-card-text>
          <p class="body-2">Select the records you want to move into a new independent group.</p>
          <!-- Side-by-side comparison content -->
          <v-row>
            <v-col cols="6" class="border-right">
              <div class="font-weight-bold mb-2">Device Instance #1</div>
              <v-sheet outlined class="pa-2 grey lighten-5 rounded">
                <div class="caption">ID: iPhone9,3</div>
                <div class="caption">OS: iOS 15.7</div>
              </v-sheet>
            </v-col>
            <v-col cols="6">
              <div class="font-weight-bold mb-2">Device Instance #2</div>
              <v-sheet outlined class="pa-2 grey lighten-5 rounded">
                <div class="caption">ID: iPhone11,8</div>
                <div class="caption">OS: iOS 17.7.1</div>
              </v-sheet>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="showSplitDialog = false">Cancel</v-btn>
          <v-btn color="error" class="text-none" @click="showSplitDialog = false">Split into new groups</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script>
export default {
  name: 'DeviceMockup2',
  data() {
    return {
      selectedIdx: 0,
      selectedDevice: null,
      showSplitDialog: false,
      newNote: '',
      devices: [
        {
          model: 'iPhone 7',
          manufacturer: 'Apple',
          type: 'smartphone',
          status: 'pending',
          firstSeen: 'Jan 10, 2024',
          lastSeen: 'Jan 20, 2025',
          lastGeo: 'Madison, WI (US)',
          os: 'iOS 15.7',
          osHistory: [
            { ver: 'iOS 15.0', date: '2024-01-10' },
            { ver: 'iOS 15.7', date: '2024-09-12' }
          ],
          notes: [{ date: '2025-03-01 14:20', text: 'Seems like person main phone until upgrade in early Jan.' }],
          diffFactors: [
            { key: 'OS Generation', vals: ['iOS 15', 'iOS 17'] },
            { key: 'Internal Identifier', vals: ['iPhone9,3', 'iPhone11,8'] }
          ],
          allAttributes: JSON.stringify({
            "device_model_identifier": "iPhone9,3",
            "user_agent_os_full": "iPhone OS 15.7",
            "user_agent_device_model": "iPhone",
            "device_model_name": "iPhone 7"
          }, null, 2)
        },
        {
          model: 'MacBook Pro 16"',
          manufacturer: 'Apple',
          type: 'laptop',
          status: 'verified',
          firstSeen: 'Nov 05, 2023',
          lastSeen: 'Feb 28, 2025',
          lastGeo: 'Madison, WI (US)',
          os: 'macOS 14.5',
          osHistory: [{ ver: '14.1', date: '2023-11-05' }, { ver: '14.5', date: '2024-06-12' }],
          notes: [],
          allAttributes: "{ ... }"
        }
      ]
    };
  },
  mounted() {
    this.selectedDevice = this.devices[0];
  },
  methods: {
    addNote() {
      if (!this.newNote.trim()) return;
      this.selectedDevice.notes.unshift({
        date: new Date().toISOString().slice(0, 16).replace('T', ' '),
        text: this.newNote
      });
      this.newNote = '';
    }
  }
};
</script>

<style scoped>
.device-list-sidebar {
  width: 280px;
  background: white;
  flex-shrink: 0;
}

.detail-container {
  background: #f8f9fa;
}

.border-right {
  border-right: 1px solid rgba(0,0,0,0.12);
}

.border-bottom {
  border-bottom: 1px solid rgba(0,0,0,0.12);
}

.border-amber-light {
  border: 1px solid #ffe082 !important;
}

.border-bottom-amber {
  border-bottom: 1px solid #ffe082;
}

.raw-box {
  background: #202124 !important;
  color: #81c995 !important;
  font-size: 11px;
  max-height: 250px;
  overflow: auto;
  border-radius: 0 0 4px 4px;
}

.gap-1 {
  gap: 4px;
}

.verification-card {
  background: #fffdf7 !important;
}

.cursor-pointer {
  cursor: pointer;
}
</style>


<script>
export default {
  name: 'DeviceMockup2',
  data() {
    return {
      selectedIdx: 0,
      selectedDevice: null,
      showMetadata: false,
      showSplitDialog: false,
      newNote: '',
      devices: [
        {
          model: 'iPhone 7',
          manufacturer: 'Apple',
          type: 'smartphone',
          status: 'pending',
          firstSeen: '2024-01-10',
          lastSeen: '2025-01-20',
          lastGeo: 'Madison, WI (US)',
          os: 'iOS 15.7',
          osHistory: [
            { ver: 'iOS 15.0', date: '2024-01-10' },
            { ver: 'iOS 15.7', date: '2024-09-12' }
          ],
          notes: [
            { date: '2025-03-01 14:20', text: 'Device identified as user main phone until upgrade in early Jan.' }
          ],
          diffFactors: [
            { key: 'OS Range', vals: ['iOS 15', 'iOS 17'] },
            { key: 'Identifier', vals: ['iPhone9,3', 'iPhone11,8'] }
          ],
          allAttributes: JSON.stringify({
            "device_model_identifier": "iPhone9,3",
            "user_agent_os_full": "iPhone OS 15.7",
            "user_agent_os.name": "iOS",
            "user_agent_device_model": "iPhone",
            "device_model_name": "iPhone 7",
            "device_manufacturer": "Apple"
          }, null, 2)
        },
        {
          model: 'iPhone XR',
          manufacturer: 'Apple',
          type: 'smartphone',
          status: 'verified',
          firstSeen: '2025-01-22',
          lastSeen: '2025-02-28',
          lastGeo: 'Chicago, IL (US)',
          os: 'iOS 17.7.1',
          osHistory: [
            { ver: 'iOS 17.7.1', date: '2025-01-22' }
          ],
          notes: [],
          allAttributes: "{ ... }"
        },
        {
          model: 'MacBook Pro 16"',
          manufacturer: 'Apple',
          type: 'laptop',
          status: 'verified',
          firstSeen: '2023-11-05',
          lastSeen: '2025-02-28',
          lastGeo: 'Madison, WI (US)',
          os: 'macOS 14.5',
          osHistory: [
            { ver: '14.1', date: '2023-11-05' },
            { ver: '14.5', date: '2024-06-12' }
          ],
          notes: [],
          allAttributes: "{ ... }"
        }
      ]
    };
  },
  mounted() {
    this.selectedDevice = this.devices[0];
  },
  methods: {
    addNote() {
      if (!this.newNote.trim()) return;
      this.selectedDevice.notes.unshift({
        date: new Date().toISOString().slice(0, 16).replace('T', ' '),
        text: this.newNote
      });
      this.newNote = '';
    }
  }
};
</script>

<style scoped>
.device-list-sidebar {
  width: 320px;
  border-right: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.detail-container {
  background: #f8f9fa;
}

.border-bottom {
  border-bottom: 1px solid #f0f0f0;
}

.border-rounded {
  border-radius: 8px !important;
}

.border-rounded-sm {
  border-radius: 4px !important;
}

.bg-grey-light {
  background: #f1f3f4;
}

.lighter-grey-bg {
  background: #fcfcfc;
}

.bg-amber-light {
  background: #fff8e1;
}

.border-bottom-amber {
  border-bottom: 1px solid #ffecb3;
}

.border-amber {
  border: 1px solid #ffecb3 !important;
}

.metadata-pre {
  background: #202124;
  color: #81c995;
  font-family: 'Roboto Mono', monospace;
  overflow: auto;
  max-height: 400px;
}

.verification-banner {
  border-left-width: 6px !important;
}

.shadow-sm {
  box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}

.collision-table .v-data-table__wrapper {
  overflow: hidden;
}

.border-right {
  border-right: 1px solid #e0e0e0;
}

.gap-2 {
  gap: 8px;
}
</style>
