// added for WISPR-lab/data-export-gui
<template>
  <v-container class="pa-6 white min-h-100" style="max-width: 1100px;">

    <h1 class="text-h4 text--primary mb-6">Devices</h1>
    
    <p class="text-body-2 text--primary" style="line-height: 1.7;">
      Data exports often contain information about currently logged-in devices in addition to lists of login events associated with some information about the origin device. 
      LEStrADE attempts to unify this data using a two-level abstraction:
    </p>

    <ul class="text-body-2 text--primary mb-10" style="line-height: 1.7;">
      <li class="mb-2">
        <strong>Device Instance</strong>: A group of one or more raw records mapping to a trusted/registered device (e.g., for 2FA) or a group of login events linked by a common identifier (e.g., session ID or serial number) or tracked across browser/app upgrades.
      </li>
      <li>
        <strong>Device Profile</strong>: A super-group of one or more <strong>device instances</strong> that share the same hardware model (e.g., Apple iPhone 11). Since you may own more than one physical device of the same model, you can reassign <strong>instances</strong> to a new or different <strong>profile</strong> 
        by selecting "Edit" in the "Device Instances" list.
      </li>
    </ul>

    <h3 class="text-h6 text--primary mb-2">Device Profiles ({{ devices.length }})</h3>

    <v-expansion-panels flat class="device-panels devices-list">
      <v-expansion-panel
        v-for="(dev, i) in devices"
        :key="i"
        class="mb-3 border rounded-xl overflow-hidden device-profile-card"
      >
        <v-expansion-panel-header class="pa-4" @click="onDeviceExpand">
          <template v-slot:default="{ open }">
            <profile-header :device="dev" :open="open" :ua-masking-text="uaMaskingText" @showJSON="showDeviceJSON" />
          </template>
        </v-expansion-panel-header>

        <v-expansion-panel-content class="grey lighten-5 border-top">
          <profile-dropdown
            :device="dev"
            :ua-masking-text="uaMaskingText"
            @change="saveDeviceChanges(dev)"
            @see-all-events="goToEvents(dev)"
            @move-instances="openMoveDialog(dev, $event)"
            @create-profile="openCreateDialog(dev, $event)"
            @showJSON="showDeviceJSON"
          />
        </v-expansion-panel-content>
      </v-expansion-panel>
    </v-expansion-panels>

    <group-modal 
      v-model="groupDialog" 
      :mode="editMode"
      :selected-instance-ids-to-move="selectedInstanceIdsToMove"
      :existing-profiles="devices"
      :source-profile-id="sourceProfileId"
      :is-loading="groupLoading"
      :error="groupError"
      @confirm="confirmGroup"
      @closed="onModalClosed"
    />

    <!-- Device JSON Modal -->
    <json-modal
      v-model="showJSONModal"
      :title="selectedDeviceForJSON ? ('Raw Data: ' + (selectedDeviceForJSON.user_label || selectedDeviceForJSON.model || selectedDeviceForJSON.label || 'Record')) : 'Data'"
      :data="selectedDeviceForJSON || {}"
      max-width="800"
    />

    <!-- Edit History Table Component -->
    <h3 class="text-h6 text--primary mb-2 font-weight-medium mt-12">Profile Edit History</h3>
    <p class="text-body-2 text--secondary mb-4">
      Edits you've made to device instances and profiles.
    </p>
    <edits-history-table :history-logs="historyLogs" :devices="devices" />
  </v-container>
</template>

<script>
import ProfileDropdown from '@/components/Devices/ProfileDropdown.vue';
import ProfileHeader from '@/components/Devices/ProfileHeader.vue';
import GroupModal from '@/components/Devices/GroupModal.vue';
import JSONModal from '@/components/Devices/JSONModal.vue';
import EditsHistoryTable from '@/components/Devices/EditsHistoryTable.vue';

export default {
  name: 'DevicesMockup',
  components: {
    ProfileDropdown,
    ProfileHeader,
    GroupModal,
    'json-modal': JSONModal,
    EditsHistoryTable
  },
  data() {
    return {
      groupDialog: false,
      editMode: 'move',
      selectedInstanceIdsToMove: [],
      sourceProfileId: '',
      groupLoading: false,
      groupError: null,
      devices: [],
      historyLogs: [],
      showJSONModal: false,
      selectedDeviceForJSON: null,

      uaMaskingText: {
        "mac_ipad": "To prevent fingerprinting, browsers on Apple iPads & Macs use generic User-Agents that hide the exact model and iOS version.",
        "iphone": "To prevent fingerprinting, browsers on iPhones use generic User-Agents that hide the exact model.",
        "profile": "Multiple physical devices may be grouped under this generic profile."
      }
    }
  },

  mounted() {
    this.fetchMockDevices();
    this.fetchMockHistory();
  },
  methods: {
    fetchMockDevices() {
      this.devices = [
        {
          id: "profile-apple-iphone7-alice",
          model: "iPhone 7",
          manufacturer: "Apple",
          os_type: "ios",
          user_label: "Alice",
          notes: "",
          label: "Alice",
          first_seen: 1737482144, // Jan 21, 2025
          last_seen: 1740009600, // Feb 20, 2025
          latest_os_version: "15.7",
          latest_os_name: "iOS",
          latest_os_type: "ios",
          instance_count: 2,
          all_os_versions: ["15.7"],
          ua_summaries: [
            { primary: "Facebook", secondary: "", color: "#5E75C2" }
          ],
          rawAttributes: {
            "device.id.facebook": "D4A6E043****************************",
            "device.manufacturer": "Apple",
            "device.model.identifier": "iPhone9,3",
            "device.model.name": "iPhone 7"
          },
          instances: [
            {
              id: "inst-fb-iphone7-alice-app",
              upload_id: "facebook-dump-zip",
              platform: "facebook",
              model: "iPhone 7",
              os_name: "iOS",
              first_seen: 1737482144,
              last_seen: 1737482144,
              upload_color: "#5E75C2",
              os_versions: ["15.7"],
              event_count: 0,
              client_ips: [],
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphone7-alice-app" },
                { label: "Model", value: "Apple iPhone 7" },
                { label: "OS", value: "iOS 15.7" },
                { label: "Device Id Facebook", value: "D4A6E043****************************" },
                { label: "User Agent Os Full", value: "iPhone OS 15.7" },
                { label: "Device Model Identifier", value: "iPhone9,3" },
                { label: "First Active", value: 1737482144, isTimestamp: true }
              ],
              ua_summary: { platform: "Facebook", color: "#5E75C2" }
            },
            {
              id: "inst-fb-iphone7-alice-session",
              upload_id: "facebook-dump-zip",
              platform: "facebook",
              model: "iPhone 7",
              os_name: "iOS",
              first_seen: 1737486987, // Jan 21, 2025
              last_seen: 1740009600, // Feb 20, 2025
              upload_color: "#5E75C2",
              os_versions: ["15.7"],
              event_count: 0,
              client_ips: ["72.33.2.108"],
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphone7-alice-session" },
                { label: "Model", value: "Apple iPhone 7" },
                { label: "OS", value: "iOS 15.7" },
                { label: "IP Addresses", value: ["72.33.2.108"] },
                { label: "Client Session Id", value: "VvKP********************" },
                { label: "User Agent Original", value: "Mozilla/5.0 (iPhone; CPU iPhone OS 15_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/19H12 [FBAN/FBIOS;FBDV/iPhone9,3;FBMD/iPhone;FBSN/iOS;FBSV/15.7;FBSS/2;FBID/phone;FBLC/en_US;FBOP/5]" },
                { label: "First Active", value: 1737486987, isTimestamp: true },
                { label: "Last Active", value: 1740009600, isTimestamp: true }
              ],
              ua_summary: { platform: "Facebook", color: "#5E75C2" }
            }
          ]
        },
        {
          id: "profile-apple-iphone-generic",
          model: "iPhone",
          manufacturer: "Apple",
          os_type: "ios",
          user_label: "iPhone",
          notes: "",
          label: "iPhone",
          first_seen: 1733702400, // Dec 9, 2024
          last_seen: 1740009600, // Feb 20, 2025
          latest_os_version: "17.7.1",
          latest_os_name: "iOS",
          latest_os_type: "ios",
          instance_count: 2,
          all_os_versions: ["17.7.1"],
          ua_summaries: [
            { primary: "Facebook", secondary: "", color: "#5E75C2" }
          ],
          rawAttributes: {
            "device.manufacturer": "Apple",
            "device.model.identifier": "iPhone",
            "client.ip": "72.33.2.118"
          },
          instances: [
            {
              id: "inst-fb-iphone-generic-session-1",
              upload_id: "facebook-dump-zip",
              platform: "facebook",
              model: "iPhone",
              os_name: "iOS",
              first_seen: 1738007083, // Jan 27, 2025
              last_seen: 1740009600, // Feb 20, 2025
              upload_color: "#5E75C2",
              apple_masking: "true",
              os_versions: ["17.7.1"],
              event_count: 0,
              client_ips: ["72.33.2.118"],
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphone-generic-session-1" },
                { label: "Model", value: "Apple iPhone" },
                { label: "OS", value: "iOS 17.7.1" },
                { label: "IP Addresses", value: ["72.33.2.118"] },
                { label: "Client Session Id", value: "IOGP********************" },
                { label: "User Agent Original", value: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148" },
                { label: "First Active", value: 1738007083, isTimestamp: true },
                { label: "Last Active", value: 1740009600, isTimestamp: true }
              ],
              ua_summary: { platform: "Facebook", color: "#5E75C2" }
            },
            {
              id: "inst-fb-iphone-generic-session-2",
              upload_id: "facebook-dump-zip",
              platform: "facebook",
              model: "iPhone",
              os_name: "iOS",
              first_seen: 1737483956, // Jan 21, 2025
              last_seen: 1737996301, // Jan 27, 2025
              upload_color: "#5E75C2",
              apple_masking: "true",
              os_versions: ["17.7.1"],
              event_count: 0,
              client_ips: ["72.33.2.118"],
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphone-generic-session-2" },
                { label: "Model", value: "Apple iPhone" },
                { label: "OS", value: "iOS 17.7.1" },
                { label: "IP Addresses", value: ["72.33.2.118"] },
                { label: "Client Session Id", value: "kuaP********************" },
                { label: "User Agent Original", value: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.8 Mobile/15E148 Safari/604.1" },
                { label: "First Active", value: 1737483956, isTimestamp: true },
                { label: "Last Active", value: 1737996301, isTimestamp: true }
              ],
              ua_summary: { platform: "Facebook", color: "#5E75C2" }
            }
          ]
        },
        {
          id: "profile-apple-iphonexr-custom",
          model: "iPhone XR",
          manufacturer: "Apple",
          os_type: "ios",
          user_label: "iPhone XR",
          notes: "",
          label: "iPhone XR",
          first_seen: 1731542400, // Nov 14, 2024
          last_seen: 1740458501, // Feb 25, 2025
          latest_os_version: "17.7.1",
          latest_os_name: "iOS",
          latest_os_type: "ios",
          instance_count: 3,
          all_os_versions: ["17.7.1"],
          ua_summaries: [
            { primary: "Facebook", secondary: "", color: "#5E75C2" }
          ],
          rawAttributes: {
            "device.id.facebook": "5D8FAD5A-34A6-4644-98AA-CB0FC61CC46A",
            "device.id.facebook_family": "5D8FAD5A****************************",
            "device.id.facebook_advertiser": "aa1960e5-d242-465a-ad74-7bade90a760e",
            "device.manufacturer": "Apple",
            "device.model.identifier": "iPhone11,8",
            "device.model.name": "iPhone XR",
            "client.ip": "2600:6c44:11f0:f010:44b8:b949:c7eb:7f04"
          },
          instances: [
            {
              id: "inst-fb-iphonexr-app",
              upload_id: "facebook-dump-zip",
              platform: "facebook",
              model: "iPhone XR",
              os_name: "iOS",
              first_seen: 1731625326,
              last_seen: 1740458501,
              upload_color: "#5E75C2",
              os_versions: ["17.7.1"],
              event_count: 0,
              client_ips: [],
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphonexr-app" },
                { label: "Model", value: "Apple iPhone XR" },
                { label: "OS", value: "iOS 17.7.1" },
                { label: "Device Id Facebook", value: "5D8FAD5A-34A6-4644-98AA-CB0FC61CC46A" },
                { label: "Device Id Facebook Family", value: "5D8FAD5A****************************" },
                { label: "Device Id Facebook Advertiser", value: "aa1960e5-d242-465a-ad74-7bade90a760e" },
                { label: "Device Model Identifier", value: "iPhone11,8" },
                { label: "User Agent Os Full", value: "iPhone OS 17.7.1" },
                { label: "First Active", value: 1731625326, isTimestamp: true },
                { label: "Last Active", value: 1740458501, isTimestamp: true }
              ],
              ua_summary: { platform: "Facebook", color: "#5E75C2" }
            },
            {
              id: "inst-fb-iphonexr-session",
              upload_id: "facebook-dump-zip",
              platform: "facebook",
              model: "iPhone XR",
              os_name: "iOS",
              first_seen: 1735850811,
              last_seen: 1740458397,
              upload_color: "#5E75C2",
              os_versions: ["17.7.1"],
              event_count: 15,
              client_ips: ["2600:6c44:11f0:f010:44b8:b949:c7eb:7f04"],
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphonexr-session" },
                { label: "Model", value: "Apple iPhone XR" },
                { label: "OS", value: "iOS 17.7.1" },
                { label: "IP Addresses", value: ["2600:6c44:11f0:f010:44b8:b949:c7eb:7f04"] },
                { label: "Client Session Id", value: "Nvt2********************" },
                { label: "User Agent Original", value: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/21H216 [FBAN/FBIOS;FBAV/492.0.0.101.111;FBBV/670308045;FBDV/iPhone11,8;FBMD/iPhone;FBSN/iOS;FBSV/17.7.1;FBSS/0;FBID/phone;FBLC/en_US;FBOP/5]" },
                { label: "First Active", value: 1735850811, isTimestamp: true },
                { label: "Last Active", value: 1740458397, isTimestamp: true }
              ],
              ua_summary: { platform: "Facebook", color: "#5E75C2" }
            },
            {
              id: "inst-fb-iphonexr-recognized",
              upload_id: "facebook-dump-zip",
              platform: "facebook",
              model: "iPhone XR",
              os_name: "iOS",
              first_seen: 1735852590,
              last_seen: 1737484029,
              upload_color: "#5E75C2",
              os_versions: ["17.7.1"],
              event_count: 0,
              client_ips: ["144.92.239.37"],
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphonexr-recognized" },
                { label: "Model", value: "Apple iPhone XR" },
                { label: "OS", value: "iOS 17.7.1" },
                { label: "IP Addresses", value: ["144.92.239.37"] },
                { label: "Client Session Id", value: "Nvt2********************" },
                { label: "User Agent Original", value: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/21H216 [FBAN/FBIOS;FBAV/492.0.0.101.111;FBBV/670308045;FBDV/iPhone11,8;FBMD/iPhone;FBSN/iOS;FBSV/17.7.1;FBSS/2;FBID/phone;FBLC/en_US;FBOP/5;FBRV/673677846]" },
                { label: "First Active", value: 1735852590, isTimestamp: true },
                { label: "Last Active", value: 1737484029, isTimestamp: true }
              ],
              ua_summary: { platform: "Facebook", color: "#5E75C2" }
            }
          ]
        }
      ];
    },
    fetchMockHistory() {
      this.historyLogs = [];
    },
    saveDeviceChanges(device) {
      console.log('Mockup: Save changes for', device.id, device.user_label, device.notes);
    },
    onDeviceExpand() {},
    showDeviceJSON(data) {
      this.selectedDeviceForJSON = data;
      this.showJSONModal = true;
    },
    goToEvents(device) {
      console.log('Mockup: go to events for', device.id);
    },
    openMoveDialog(device, instanceIds) {
      this.editMode = 'move';
      this.selectedInstanceIdsToMove = instanceIds;
      this.sourceProfileId = device.id;
      this.groupError = null;
      this.groupDialog = true;
    },
    openCreateDialog(device, instanceIds) {
      this.editMode = 'create';
      this.selectedInstanceIdsToMove = instanceIds;
      this.sourceProfileId = device.id;
      this.groupError = null;
      this.groupDialog = true;
    },
    confirmGroup(payload) {
      console.log('Mockup: confirmGroup', payload);
      this.groupDialog = false;
    },
    onModalClosed() {
      this.groupDialog = false;
    }
  }
}
</script>

<style scoped>
.min-h-100 {
  min-height: 100vh;
}
.border {
  border: 1px solid #e0e0e0;
}
.border-top {
  border-top: 1px solid #e0e0e0;
}
</style>
