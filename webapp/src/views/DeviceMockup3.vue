<template>
  <v-container fluid class="pa-4 grey lighten-5 min-h-100">
    <!-- 1. Explainer/Disclaimer Section -->
    <v-row>
      <v-col cols="12">
        <v-alert
          border="left"
          colored-border
          type="info"
          elevation="1"
          class="white"
        >
          <div class="text-h6 mb-1">Asset Verification & Grouping</div>
          <div class="body-2 grey--text text--darken-2">
            This workspace helps you organize technical event records into physical household <strong>Assets</strong>. 
            Because data exports often include generic labels (e.g., "iPhone"), you can manually refine 
            your inventory by dragging <strong>Unassigned Records</strong> into the correct <strong>Confirmed Device Group</strong>.
          </div>
        </v-alert>
      </v-col>
    </v-row>

    <!-- 2. Main Interaction Area: Unassigned vs Confirmed -->
    <v-row>
      <!-- LEFT: Unassigned/Generic Records (Merge Type 2 Candidates) -->
      <v-col cols="12" md="4">
        <v-card flat outlined class="h-100">
          <v-toolbar flat dense color="grey lighten-4" class="border-bottom">
            <v-icon left small color="orange">mdi-tray-arrow-down</v-icon>
            <v-toolbar-title class="caption font-weight-bold text-uppercase">Potential Unassigned Assets</v-toolbar-title>
          </v-toolbar>
          
          <v-list dense class="pa-2 overflow-y-auto" style="max-height: 70vh">
            <v-list-item-group>
              <v-list-item 
                v-for="(item, i) in unassigned" 
                :key="i"
                class="mb-2 rounded border"
                style="cursor: grab; background: white;"
                draggable
                @dragstart="onDragStart(item)"
                @dragend="onDragEnd"
              >
                <v-list-item-content>
                  <div class="d-flex justify-space-between align-center mb-1">
                    <span class="body-2 font-weight-bold">{{ item.label }}</span>
                    <v-chip x-small color="grey lighten-3" label>{{ item.os }}</v-chip>
                  </div>
                  <div class="caption grey--text d-flex align-center">
                    <v-icon x-small class="mr-1">mdi-map-marker</v-icon> {{ item.city }}
                    <v-spacer></v-spacer>
                    <v-btn x-small text color="primary" class="text-none px-1" @click.stop="openRecordDetails(item)">
                      View Record
                    </v-btn>
                  </div>
                  <!-- Hints for Dragging (Heuristics) -->
                  <div v-if="item.hint" class="mt-2 py-1 px-2 rounded amber lighten-5 border-amber d-flex align-start">
                    <v-icon x-small color="amber darken-4" class="mr-1 mt-1">mdi-lightbulb-on-outline</v-icon>
                    <span class="caption amber--text text--darken-4 font-weight-bold leading-tight">{{ item.hint }}</span>
                  </div>
                </v-list-item-content>
              </v-list-item>
            </v-list-item-group>
          </v-list>

          <v-card-text v-if="unassigned.length === 0" class="text-center py-10 grey--text">
            <v-icon size="48" color="grey lighten-3">mdi-check-circle-outline</v-icon>
            <div class="caption mt-2">All records are assigned to devices</div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- RIGHT: Confirmed Device Groups (Targets) -->
      <v-col cols="12" md="8">
        <v-card flat outlined class="h-100">
          <v-toolbar flat dense color="blue-grey lighten-5" class="border-bottom">
            <v-icon left small color="primary">mdi-devices</v-icon>
            <v-toolbar-title class="caption font-weight-bold text-uppercase">Confirmed Household Devices</v-toolbar-title>
            <v-spacer></v-spacer>
            <v-btn small text color="primary" class="text-none">
              <v-icon left small>mdi-plus</v-icon> Add Device
            </v-btn>
          </v-toolbar>

          <v-container fluid class="pa-4">
            <v-row dense>
              <v-col v-for="(dev, i) in devices" :key="i" cols="12" sm="6">
                <!-- Drop Target styling -->
                <v-hover v-slot="{ hover }">
                  <v-card 
                    outlined 
                    :class="['transition-swing mb-2', hover ? 'elevation-3 border-primary' : '']"
                    @click="openGroupDetails(dev)"
                    style="cursor: pointer"
                    @dragover.prevent
                    @drop="onDrop(dev)"
                  >
                    <v-card-text class="pa-3">
                      <div class="d-flex align-center mb-2">
                        <v-avatar size="36" :color="dev.status === 'Needs Verification' ? 'amber lighten-5' : 'blue lighten-5'" class="mr-3">
                          <v-icon :color="dev.status === 'Needs Verification' ? 'amber darken-2' : 'primary'" small>{{ dev.icon }}</v-icon>
                        </v-avatar>
                        <div class="overflow-hidden">
                          <div class="body-1 font-weight-bold text-truncate black--text">{{ dev.model }}</div>
                          <div class="caption grey--text">{{ dev.manufacturer }}</div>
                        </div>
                        <v-spacer></v-spacer>
                        <v-chip x-small outlined color="grey darken-1">{{ dev.recordCount }} records</v-chip>
                      </div>

                      <v-divider class="my-2"></v-divider>
                      
                      <div class="d-flex align-center justify-space-between">
                        <v-chip 
                          x-small 
                          label
                          :color="dev.status === 'Needs Verification' ? 'amber lighten-4' : 'blue lighten-4'"
                          :class="dev.status === 'Needs Verification' ? 'amber--text text--darken-4' : 'blue--text text--darken-4'"
                          class="font-weight-bold"
                        >
                          <v-icon left x-small v-if="dev.status === 'Needs Verification'">mdi-alert-circle</v-icon>
                          <v-icon left x-small v-else>mdi-check-decagram</v-icon>
                          {{ dev.status }}
                        </v-chip>
                        <span class="caption grey--text font-italic">Seen {{ dev.lastSeen }}</span>
                      </div>
                    </v-card-text>
                    
                    <!-- Drag Target Indicator -->
                    <v-overlay absolute v-if="isDragging && hover" color="primary" opacity="0.1">
                      <v-icon large color="primary">mdi-plus-box</v-icon>
                      <div class="caption primary--text font-weight-bold mt-2">Drop to Merge</div>
                    </v-overlay>
                  </v-card>
                </v-hover>
              </v-col>
            </v-row>
          </v-container>
        </v-card>
      </v-col>
    </v-row>

    <!-- 3. Confirm Merge Dialog (Triggered by drag-and-drop) -->
    <v-dialog v-model="mergeDialog" max-width="700" persistent>
      <v-card v-if="stagingMerge" class="rounded-lg">
        <v-card-title class="headline font-weight-bold primary white--text">
          <v-icon left dark>mdi-merge</v-icon>
          Confirm Asset Assignment
        </v-card-title>
        
        <v-card-text class="pa-6">
          <p class="body-1">Are you sure you want to assign this unassigned record to the <strong>{{ stagingMerge.target.model }}</strong>?</p>
          
          <v-row class="mt-4">
            <!-- UNASSIGNED SOURCE -->
            <v-col cols="5">
              <v-card outlined flat class="pa-3 grey lighten-5 h-100">
                <div class="caption font-weight-bold grey--text text-uppercase mb-2">Unassigned Record</div>
                <div class="body-1 font-weight-bold mb-1">{{ stagingMerge.source.label }}</div>
                <v-chip x-small color="grey lighten-2">{{ stagingMerge.source.os }}</v-chip>
                <div class="caption mt-2 grey--text">{{ stagingMerge.source.city }}</div>
              </v-card>
            </v-col>

            <!-- CONNECTOR -->
            <v-col cols="2" class="d-flex align-center justify-center">
              <v-icon large color="grey lighten-1">mdi-arrow-right-thick</v-icon>
            </v-col>

            <!-- TARGET DEVICE GROUP -->
            <v-col cols="5">
              <v-card outlined flat class="pa-3 blue lighten-5 h-100 border-primary">
                <div class="caption font-weight-bold primary--text text-uppercase mb-2">Target Asset Group</div>
                <div class="body-1 font-weight-bold mb-1">{{ stagingMerge.target.model }}</div>
                <v-chip x-small color="primary" outlined>{{ stagingMerge.target.osHistory[0] }}+</v-chip>
                <div class="caption mt-2 primary--text">{{ stagingMerge.target.lastSeen }}</div>
              </v-card>
            </v-col>
          </v-row>

          <v-alert
            v-if="stagingMerge.source.os.split(' ')[0] !== stagingMerge.target.osHistory[0].split(' ')[0]"
            type="warning"
            text
            dense
            class="mt-6 mb-0"
          >
            <div class="subtitle-2 font-weight-bold">Hardware Mismatch Warning</div>
            <div class="caption">The unassigned record reports <strong>{{ stagingMerge.source.os }}</strong> while the target group uses <strong>{{ stagingMerge.target.osHistory[0] }}</strong>. These might be different physical devices.</div>
          </v-alert>
          <v-alert
            v-else
            type="success"
            text
            dense
            class="mt-6 mb-0"
          >
            <div class="caption font-weight-bold">Pattern Match: High probability match based on OS and Location.</div>
          </v-alert>
        </v-card-text>

        <v-divider></v-divider>
        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn text class="text-none mr-2" @click="cancelMerge">Cancel</v-btn>
          <v-btn color="primary" depressed class="px-6 text-none font-weight-bold" @click="confirmMerge">
            Complete Assignment
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 4. Detail Modals -->
    <v-dialog v-model="groupDialog" max-width="900" scrollable transition="dialog-bottom-transition">
      <v-card v-if="selectedGroup" class="rounded-lg">
        <v-toolbar flat color="white" class="border-bottom sticky-toolbar">
          <v-avatar size="40" :color="selectedGroup.status === 'Needs Verification' ? 'amber lighten-5' : 'blue lighten-5'" class="mr-3">
            <v-icon :color="selectedGroup.status === 'Needs Verification' ? 'amber darken-2' : 'primary'">{{ selectedGroup.icon }}</v-icon>
          </v-avatar>
          <div>
            <v-toolbar-title class="headline font-weight-bold">{{ selectedGroup.model }}</v-toolbar-title>
            <span class="caption grey--text">{{ selectedGroup.manufacturer }} &bull; Profile Overview</span>
          </div>
          <v-spacer></v-spacer>
          <v-btn icon @click="groupDialog = false"><v-icon>mdi-close</v-icon></v-btn>
        </v-toolbar>

        <v-card-text class="pa-6">
          <v-row>
            <!-- Forensic Summary -->
            <v-col cols="12" md="7">
              <section class="mb-6">
                <div class="caption font-weight-black grey--text text-uppercase mb-2 letter-spacing-1">Conflict Detection</div>
                <v-card outlined v-if="selectedGroup.status === 'Needs Verification'" class="pa-0 overflow-hidden border-amber">
                  <div class="amber lighten-5 pa-3 d-flex align-center border-bottom-amber">
                    <v-icon small color="amber darken-4" class="mr-2">mdi-alert-outline</v-icon>
                    <span class="body-2 font-weight-bold amber--text text--darken-4">Multiple Hardware Indicators</span>
                  </div>
                  <v-simple-table dense>
                    <template v-slot:default>
                      <thead>
                        <tr class="grey lighten-5">
                          <th class="caption font-weight-bold">Property</th>
                          <th class="caption font-weight-bold text-right">Differing Values</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(factor, idx) in selectedGroup.diffFactors" :key="idx">
                          <td class="caption font-weight-bold py-2">{{ factor.key }}</td>
                          <td class="text-right py-1">
                            <v-chip v-for="val in factor.vals" :key="val" x-small color="red lighten-5" class="red--text font-weight-bold ml-1">
                              {{ val }}
                            </v-chip>
                          </td>
                        </tr>
                      </tbody>
                    </template>
                  </v-simple-table>
                </v-card>
                <v-alert v-else type="success" text dense class="mb-0">
                  <span class="caption pt-1">No hardware conflicts detected for this asset.</span>
                </v-alert>
              </section>

              <section>
                <div class="caption font-weight-black grey--text text-uppercase mb-2 letter-spacing-1">Activity Context</div>
                <v-row dense>
                  <v-col cols="6">
                    <v-sheet outlined class="pa-3 rounded grey lighten-5">
                      <div class="overline grey--text mb-1">First Record</div>
                      <div class="body-2 font-weight-medium">{{ selectedGroup.firstSeen }}</div>
                    </v-sheet>
                  </v-col>
                  <v-col cols="6">
                    <v-sheet outlined class="pa-3 rounded grey lighten-5">
                      <div class="overline grey--text mb-1">Latest Record</div>
                      <div class="body-2 font-weight-medium">{{ selectedGroup.lastSeen }}</div>
                    </v-sheet>
                  </v-col>
                  <v-col cols="12" class="mt-2">
                    <v-sheet outlined class="pa-3 rounded grey lighten-5">
                      <div class="overline grey--text mb-2">Authenticated OS Timeline</div>
                      <div class="d-flex flex-wrap gap-1">
                        <v-chip v-for="os in selectedGroup.osHistory" :key="os" x-small outlined color="primary" class="font-weight-bold">{{ os }}</v-chip>
                      </div>
                    </v-sheet>
                  </v-col>
                </v-row>
              </section>
            </v-col>

            <!-- Group Members -->
            <v-col cols="12" md="5">
               <v-card outlined class="pa-0 h-100 d-flex flex-column">
                <div class="caption font-weight-black grey--text text-uppercase pa-3 grey lighten-4 border-bottom d-flex align-center">
                  Associated Records
                  <v-spacer></v-spacer>
                  <v-chip x-small color="grey lighten-2">{{ selectedGroup.recordCount }}</v-chip>
                </div>
                <v-list subheader dense class="flex-grow-1 overflow-y-auto" style="max-height: 450px;">
                  <v-list-item v-for="n in selectedGroup.recordCount" :key="n" class="border-bottom px-4">
                    <v-list-item-avatar size="24" color="grey lighten-4">
                      <v-icon x-small color="grey darken-1">mdi-file-document-outline</v-icon>
                    </v-list-item-avatar>
                    <v-list-item-content>
                      <v-list-item-title class="caption font-weight-bold">Event #{{1020 + n * 7}}</v-list-item-title>
                      <v-list-item-subtitle class="x-small-text">Source: Facebook Session</v-list-item-subtitle>
                    </v-list-item-content>
        </v-list-item>
                </v-list>
              </v-card>
            </v-col>
          </v-row>
        </v-card-text>

        <v-divider></v-divider>
        <v-card-actions class="pa-4 grey lighten-4">
          <v-btn text color="error" class="text-none font-weight-bold">Dissolve Asset Group</v-btn>
          <v-spacer></v-spacer>
          <v-btn depressed color="primary" class="px-6 text-none font-weight-bold" @click="groupDialog = false">
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 5. Single Record Detail -->
    <v-dialog v-model="recordDialog" max-width="600">
       <v-card v-if="selectedRecord" class="rounded-lg overflow-hidden">
         <v-toolbar flat dark color="grey darken-3">
           <v-toolbar-title class="subtitle-1">Detail: {{ selectedRecord.label }}</v-toolbar-title>
           <v-spacer></v-spacer>
           <v-btn icon @click="recordDialog = false"><v-icon>mdi-close</v-icon></v-btn>
         </v-toolbar>
         <v-card-text class="pa-4">
           <div class="caption font-weight-black mb-2 grey--text">METADATA</div>
           <pre class="raw-box pa-3">{{ JSON.stringify(selectedRecord.raw, null, 2) }}</pre>
         </v-card-text>
         <v-card-actions class="pa-4 border-top">
           <v-spacer></v-spacer>
           <v-btn depressed color="primary" @click="recordDialog = false">Close</v-btn>
         </v-card-actions>
       </v-card>
    </v-dialog>

  </v-container>
</template>

<script>
export default {
  name: 'DeviceMockup3',
  data() {
    return {
      isDragging: false,
      groupDialog: false,
      recordDialog: false,
      mergeDialog: false,
      selectedGroup: null,
      selectedRecord: null,
      stagingMerge: null,
      unassigned: [
        { 
          label: 'iPhone (Generic)', 
          os: 'iOS 15.7', 
          city: 'Madison, WI', 
          hint: 'Matches location & OS of "iPhone 7"',
          raw: { "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_7_1 like Mac OS X)...", "ip": "72.33.1.5" } 
        },
        { 
          label: 'iPhone (Generic)', 
          os: 'iOS 17.7', 
          city: 'Chicago, IL', 
          hint: 'Matches location of "iPhone XR"',
          raw: { "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X)...", "ip": "64.233.191.1" } 
        },
        { 
          label: 'Unknown Macintosh', 
          os: 'macOS 14.5', 
          city: 'Madison, WI', 
          hint: 'Shared subnet with MacBook Pro 16"',
          raw: { "model_id": "MacBookPro18,3", "os_version": "14.5.0" } 
        }
      ],
      devices: [
        {
          model: 'iPhone 7',
          manufacturer: 'Apple',
          icon: 'mdi-cellphone',
          status: 'Needs Verification',
          recordCount: 12,
          firstSeen: '2024-01-10',
          lastSeen: '2025-01-20',
          osHistory: ['iOS 15.0', 'iOS 15.7'],
          diffFactors: [{ key: 'Hardware ID', vals: ['iPhone9,3', 'iPhone11,8'] }]
        },
        {
          model: 'iPhone XR',
          manufacturer: 'Apple',
          icon: 'mdi-cellphone',
          status: 'Verified',
          recordCount: 45,
          firstSeen: '2025-01-22',
          lastSeen: '2025-02-28',
          osHistory: ['iOS 17.7.1'],
          diffFactors: []
        },
        {
          model: 'MacBook Pro 16"',
          manufacturer: 'Apple',
          icon: 'mdi-laptop',
          status: 'Verified',
          recordCount: 8,
          firstSeen: '2023-11-05',
          lastSeen: '2025-02-28',
          osHistory: ['macOS 14.5'],
          diffFactors: []
        }
      ]
    };
  },
  methods: {
    openGroupDetails(group) {
      if (this.isDragging) return;
      this.selectedGroup = group;
      this.groupDialog = true;
    },
    openRecordDetails(record) {
      this.selectedRecord = record;
      this.recordDialog = true;
    },
    onDragStart(record) {
      this.isDragging = true;
      this.selectedRecord = record;
    },
    onDragEnd() {
      setTimeout(() => { this.isDragging = false; }, 100);
    },
    onDrop(targetGroup) {
      if (!this.selectedRecord) return;
      this.stagingMerge = { source: this.selectedRecord, target: targetGroup };
      this.mergeDialog = true;
    },
    confirmMerge() {
      const idx = this.unassigned.indexOf(this.stagingMerge.source);
      if (idx > -1) this.unassigned.splice(idx, 1);
      this.stagingMerge.target.recordCount++;
      this.stagingMerge.target.status = 'Needs Verification';
      this.mergeDialog = false;
      this.stagingMerge = null;
    },
    cancelMerge() {
      this.mergeDialog = false;
      this.stagingMerge = null;
    }
  }
};
</script>

<style scoped>
.min-h-100 { min-height: 100%; }
.border { border: 1px solid rgba(0,0,0,0.12) !important; }
.border-bottom { border-bottom: 1px solid rgba(0,0,0,0.12) !important; }
.border-primary { border: 1px solid #1976d2 !important; }
.border-amber { border: 1px solid #ffe082 !important; }
.border-bottom-amber { border-bottom: 1px solid #ffe082 !important; }
.raw-box {
  background: #202124;
  color: #81c995;
  font-family: monospace;
  font-size: 11px;
  max-height: 250px;
  overflow: auto;
  border-radius: 4px;
}
.sticky-toolbar { position: sticky; top: 0; z-index: 5; }
.leading-tight { line-height: 1.2; }
.x-small-text { font-size: 10px; }
</style>
