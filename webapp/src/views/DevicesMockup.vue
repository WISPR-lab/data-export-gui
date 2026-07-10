// added for WISPR-lab/data-export-gui
<template>
  <v-container class="pa-6 white min-h-100" style="max-width: 1200px;">

    <!-- Page Header -->
    <div class="mb-6">
      <h1 class="text-h4 text--primary mb-1">Devices</h1>
      <div class="text-body-2 text--secondary">Track account access records and unlinked activity clusters.</div>
    </div>

    <!-- Generic Platform Loop -->
    <v-card 
      v-for="(platform, platformIdx) in platforms"
      :key="'platform-' + platformIdx"
      outlined 
      class="pa-5 rounded-xl mb-6 shadow-sm" 
      style="background-color: white;"
    >
      <!-- Platform Header -->
      <div class="d-flex align-center mb-5">
        <v-avatar size="44" :color="platform.color" class="mr-3">
          <v-icon color="white" size="26">{{ platform.icon }}</v-icon>
        </v-avatar>
        <div>
          <h2 class="text-subtitle-1 text--primary font-weight-medium mb-0">{{ platform.displayName }} Account</h2>
          <div class="text-caption text--secondary">{{ platform.accountLabel }}</div>
        </div>
      </div>

      <!-- Two-Column Grid Within Each Platform -->
      <v-row>
        
        <!-- COLUMN 1: Sessions & Registrations (Left side) -->
        <v-col cols="12" md="6" class="pr-md-4">
          <h3 class="text-subtitle-2 font-weight-bold grey--text text--darken-2 mb-1">Sessions & Registrations</h3>
          <p class="text-caption text--secondary mb-4">Registered sessions and hardware records on the platform.</p>
          
          <v-expansion-panels flat class="device-panels">
            <v-expansion-panel
              v-for="(entry, eIdx) in platform.entries"
              :key="'entry-' + eIdx"
              class="mb-3 border rounded-xl overflow-hidden device-profile-card"
            >
              <v-expansion-panel-header class="pa-4">
                <template v-slot:default="{ open }">
                  <div class="device-header-row py-1 d-flex align-center justify-space-between w-100">
                    <div class="d-flex align-center flex-grow-1 min-width-0">
                      <v-avatar size="40" color="grey lighten-5" class="mr-4 flex-shrink-0">
                        <v-icon color="grey darken-3" size="20">{{ entry.icon }}</v-icon>
                      </v-avatar>
                      
                      <div class="d-flex flex-column min-width-0">
                        <div class="d-flex flex-wrap align-baseline">
                          <span class="text-subtitle-2 text--primary font-weight-medium text-truncate">
                            {{ entry.title }}
                          </span>
                          <span v-if="entry.norm_client" class="text-caption text--secondary font-weight-regular ml-2">
                            via {{ entry.norm_client }}
                          </span>
                        </div>
                        <div v-if="entry.dateString || entry.location" class="text-caption text--secondary mt-0.5 text-truncate">
                          <span>{{ entry.dateString }}</span>
                          <span v-if="entry.dateString && entry.location"> • </span>
                          <span>{{ entry.location }}</span>
                        </div>
                      </div>
                    </div>
                    
                    <!-- Right Side: Chips & Action Button -->
                    <div class="text-right mr-4 flex-shrink-0 d-flex align-center justify-end" style="gap: 8px;">
                      <!-- Fingerprint Chip -->
                      <v-tooltip v-if="entry.is_reduced_ua" bottom max-width="320">
                        <template v-slot:activator="{ on, attrs }">
                          <v-chip
                            small
                            color="grey lighten-2"
                            class="font-weight-medium flex-shrink-0 grey--text text--darken-3 px-2"
                            style="height: 22px; font-size: 11px;"
                            v-bind="attrs"
                            v-on="on"
                          >
                            <v-icon left small class="grey--text text--darken-3" style="font-size: 12px; margin-right: 4px;">mdi-fingerprint-off</v-icon>
                            Reduced UA
                          </v-chip>
                        </template>
                        <span>To prevent fingerprinting, browsers on iPhones use generic User-Agents that hide the exact model.</span>
                      </v-tooltip>

                      <!-- Cookie Chip -->
                      <v-chip 
                        v-if="entry.augmented_from_recognized" 
                        small 
                        color="primary" 
                        outlined
                        class="px-2"
                        style="height: 22px; font-size: 11px;"
                      >
                        Cookie
                      </v-chip>

                      <!-- Action Button -->
                      <v-btn
                        v-if="entry.event_count"
                        text
                        small
                        color="primary"
                        class="text-capitalize px-1 min-width-0"
                        style="height: 28px; font-size: 12px;"
                        @click.stop="goToEventsPage(entry.query)"
                      >
                        {{ entry.event_count }} Events
                        <v-icon right small style="margin-left: 2px; font-size: 14px;">mdi-arrow-right</v-icon>
                      </v-btn>
                    </div>
                  </div>
                </template>
              </v-expansion-panel-header>

              <v-expansion-panel-content class="grey lighten-5 border-top">
                <div class="pa-4">
                  <div class="text-caption text--primary font-weight-medium mb-2">
                    {{ getDetailsTitle(entry.entity_type) }}
                  </div>
                  <attributes-table :attributes="entry.formatted_attributes" />
                </div>
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-col>

        <!-- COLUMN 2: Unlinked Activity (Right side) -->
        <v-col cols="12" md="6" class="pl-md-4 border-left">
          <h3 class="text-subtitle-2 font-weight-bold grey--text text--darken-2 mb-1">Unlinked Activity</h3>
          <p class="text-caption text--secondary mb-4">
            Logins/activity with no session cookie. Could belong to any matching device.
          </p>
          
          <!-- Visually distinct, non-rounded, dashed-border list rows for clusters -->
          <div class="d-flex flex-column" style="gap: 12px;">
            <div
              v-for="(cluster, cIdx) in platform.unlinkedClusters"
              :key="'cluster-' + cIdx"
              class="unlinked-activity-row pa-3 d-flex align-center justify-space-between"
            >
              <div class="min-width-0">
                <div class="text-caption font-weight-bold text--primary text-truncate">
                  UNLINKED ACTIVITY BLOCK
                </div>
                <div class="text-caption text--secondary mt-0.5 text-truncate">
                  {{ cluster.event_count }} Logins on {{ cluster.title }}
                  <span v-if="cluster.norm_client"> via {{ cluster.norm_client }}</span>
                </div>
                <div class="text-caption text--secondary text-truncate">
                  Active {{ cluster.dateString }}
                </div>
              </div>

              <!-- View Events link -->
              <v-btn
                v-if="cluster.event_count"
                small
                text
                color="primary"
                class="text-capitalize px-2 font-weight-medium"
                @click.stop="goToEventsPage(cluster.query)"
              >
                View {{ cluster.event_count }} Events
                <v-icon right size="14" class="ml-1">mdi-arrow-right</v-icon>
              </v-btn>
            </div>
          </div>
        </v-col>

      </v-row>
    </v-card>

  </v-container>
</template>

<script>
import AttributesTable from '@/components/Devices/AttributesTable.vue';

export default {
  name: 'DevicesMockup',
  components: {
    AttributesTable
  },
  data() {
    return {
      platforms: []
    }
  },
  mounted() {
    this.fetchMockData();
  },
  methods: {
    getDetailsTitle(type) {
      const titles = {
        'session': 'Session Attributes',
        'app_registration': 'App Registration Attributes',
        'hardware_registration': 'Hardware Registration Attributes',
        'trusted_cookie': 'Trusted Cookie Attributes',
        'platform_inferred_device': 'Platform Inferred Device Attributes'
      };
      return titles[type] || 'Connection Attributes';
    },
    goToEventsPage(query) {
      if (this.$router) {
        const routeName = this.$route.name === 'DemoDevices' ? 'DemoEvents' : 'Events';
        this.$router.push({
          name: routeName,
          query: { q: query }
        }).catch(err => {});
      }
    },
    fetchMockData() {
      this.platforms = [
        {
          name: "facebook",
          displayName: "Facebook",
          accountLabel: "Alice (alice_fb_123)",
          icon: "mdi-facebook",
          color: "#5E75C2",
          entries: [
            {
              entity_type: "session",
              title: "iPhone XR",
              dateString: "Active Jan 3, 2025 – Feb 25, 2025",
              icon: "mdi-cookie-outline",
              norm_client: "Facebook App",
              location: "Madison, WI",
              is_reduced_ua: false,
              augmented_from_recognized: true,
              event_count: 14,
              query: "session_id:inst-fb-iphonexr-session",
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphonexr-session" },
                { label: "Model", value: "Apple iPhone XR" },
                { label: "OS", value: "iOS 17.7.1" },
                { label: "IP Addresses", value: ["2600:6c44:11f0:f010:44b8:b949:c7eb:7f04", "144.92.239.37"] },
                { label: "Client Session Id", value: "Nvt2********************" },
                { label: "User Agent Original", value: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/21H216 [FBAN/FBIOS;FBAV/492.0.0.101.111;FBBV/6703080455;FBDV/iPhone11,8;FBMD/iPhone;FBSN/iOS;FBSV/17.7.1;FBSS/0;FBID/phone;FBLC/en_US;FBOP/5]" },
                { label: "Name", value: "Facebook for iOS on Apple iPhone XR" },
                { label: "Device", value: "iPhone XR" },
                { label: "Location", value: "Madison, WI, United States" },
                { label: "App", value: "Facebook app" },
                { label: "Session Type", value: "iphone" },
                { label: "First Active", value: 1735850811, isTimestamp: true },
                { label: "Last Active", value: 1740458397, isTimestamp: true }
              ]
            },
            {
              entity_type: "session",
              title: "iPhone (Generic)",
              dateString: "Last Active: Jan 27, 2025",
              icon: "mdi-cookie-outline",
              norm_client: "UIWebView",
              location: "Madison, WI",
              is_reduced_ua: true,
              augmented_from_recognized: false,
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphone-generic-session-1" },
                { label: "Model", value: "Apple iPhone" },
                { label: "OS", value: "iOS 17.7.1" },
                { label: "IP Addresses", value: ["72.33.2.118"] },
                { label: "Client Session Id", value: "IOGP********************" },
                { label: "User Agent Original", value: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148" },
                { label: "Device", value: "iPhone" },
                { label: "Location", value: "Madison, WI, United States" },
                { label: "App", value: "UIWebView" },
                { label: "Session Type", value: "mobile_web" },
                { label: "First Active", value: 1738007083, isTimestamp: true }
              ]
            },
            {
              entity_type: "session",
              title: "iPhone (Generic)",
              dateString: "Active Jan 21, 2025 – Jan 27, 2025",
              icon: "mdi-cookie-outline",
              norm_client: "Mobile Safari",
              location: "Madison, WI",
              is_reduced_ua: true,
              augmented_from_recognized: false,
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphone-generic-session-2" },
                { label: "Model", value: "Apple iPhone" },
                { label: "OS", value: "iOS 17.7.1" },
                { label: "IP Addresses", value: ["72.33.2.118"] },
                { label: "Client Session Id", value: "kuaP********************" },
                { label: "User Agent Original", value: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.8 Mobile/15E148 Safari/604.1" },
                { label: "Device", value: "iPhone" },
                { label: "Location", value: "Madison, WI, United States" },
                { label: "App", value: "Mobile Safari" },
                { label: "Session Type", value: "mobile_web" },
                { label: "First Active", value: 1737483956, isTimestamp: true },
                { label: "Last Active", value: 1737996301, isTimestamp: true }
              ]
            },
            {
              entity_type: "session",
              title: "iPhone 7",
              dateString: "Last Active: Jan 21, 2025",
              icon: "mdi-cookie-outline",
              norm_client: "Facebook App",
              location: "Madison, WI",
              is_reduced_ua: false,
              augmented_from_recognized: false,
              event_count: 6,
              query: "session_id:inst-fb-iphone7-alice-session",
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphone7-alice-session" },
                { label: "Model", value: "Apple iPhone 7" },
                { label: "OS", value: "iOS 15.7" },
                { label: "IP Addresses", value: ["72.33.2.108"] },
                { label: "Client Session Id", value: "VvKP********************" },
                { label: "User Agent Original", value: "Mozilla/5.0 (iPhone; CPU iPhone OS 15_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/19H12 [FBAN/FBIOS;FBAV/492.0.0.101.111;FBBV/6703080455;FBDV/iPhone9,3;FBMD/iPhone;FBSN/iOS;FBSV/15.7;FBSS/2;FBID/phone;FBLC/en_US;FBOP/5]" },
                { label: "Device", value: "iPhone" },
                { label: "Location", value: "Madison, WI, United States" },
                { label: "App", value: "Facebook for iOS" },
                { label: "Session Type", value: "web" },
                { label: "First Active", value: 1737486987, isTimestamp: true }
              ]
            },
            {
              entity_type: "app_registration",
              title: "iPhone XR",
              dateString: "Last Active: Feb 25, 2025",
              icon: "mdi-cellphone-link",
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphonexr-app" },
                { label: "Model", value: "Apple iPhone XR" },
                { label: "OS", value: "iOS 17.7.1" },
                { label: "Type", value: "iPhone11,8" },
                { label: "Os", value: "iPhone OS 17.7.1" },
                { label: "Advertiser Id", value: "aa1960e5-d242-465a-ad74-7bade90a760e" },
                { label: "Family Device Id", value: "5D8FAD5A****************************" },
                { label: "Device Locale", value: "en_US" },
                { label: "Push Tokens", value: [
                  "Token 1: 8e63... (device_id: 5D8FAD5A-34A6-4644-98AA-CB0FC61CC46A, app_version: 492.0.0.101.111, os: 17.7.1, created: Jan 3, 2025)",
                  "Token 2: db24... (device_id: 5D8FAD5A-34A6-4644-98AA-CB0FC61CC46A, app_version: 492.0.0.101.111, os: 17.7.1, created: Nov 14, 2024)"
                ] },
                { label: "First Active", value: 1731625326, isTimestamp: true },
                { label: "Last Active", value: 1740458501, isTimestamp: true }
              ]
            },
            {
              entity_type: "app_registration",
              title: "iPhone 7",
              dateString: "Last Active: Jan 21, 2025",
              icon: "mdi-cellphone-link",
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphone7-alice-app" },
                { label: "Model", value: "Apple iPhone 7" },
                { label: "OS", value: "iOS 15.7" },
                { label: "Type", value: "iPhone9,3" },
                { label: "Os", value: "iPhone OS 15.7" },
                { label: "Family Device Id", value: "D4A6E043****************************" },
                { label: "Device Locale", value: "en_US" },
                { label: "Update Time", value: "1737482144", isTimestamp: true }
              ]
            }
          ],
          unlinkedClusters: [
            {
              title: "iPhone (Generic)",
              norm_client: "Facebook App",
              dateString: "Jan 21, 2025 – Feb 20, 2025",
              event_count: 16,
              query: "app:fb_generic_ios"
            },
            {
              title: "iPhone (Generic)",
              norm_client: "Mobile Safari",
              dateString: "Jun 8, 2025 – Jun 12, 2025",
              event_count: 8,
              query: "browser:safari_generic_ios"
            }
          ]
        },
        {
          name: "google",
          displayName: "Google",
          accountLabel: "Alice (alice@gmail.com)",
          icon: "mdi-google",
          color: "#FD7EAC",
          entries: [
            {
              entity_type: "platform_inferred_device",
              title: "iPhone XR",
              dateString: "Last Active: Feb 19, 2025",
              icon: "mdi-account-clock-outline",
              location: "US",
              is_reduced_ua: false,
              formatted_attributes: [
                { label: "Device Type", value: "MOBILE" },
                { label: "Brand Name", value: "Apple" },
                { label: "Marketing Name", value: "iPhone XR" },
                { label: "OS", value: "iOS" },
                { label: "OS Version", value: "17.7.1" },
                { label: "Device Model", value: "iPhone11,8" },
                { label: "User Given Name", value: "iPhone" },
                { label: "Device Last Location", value: "Country ISO: US\nLast Activity Time: 2025-02-19 14:40:00 UTC" }
              ]
            },
            {
              entity_type: "platform_inferred_device",
              title: "iPhone (Generic)",
              dateString: "Last Active: Feb 20, 2025",
              icon: "mdi-account-clock-outline",
              location: "US",
              is_reduced_ua: true,
              formatted_attributes: [
                { label: "Device Type", value: "MOBILE" },
                { label: "Brand Name", value: "Apple" },
                { label: "Marketing Name", value: "iPhone" },
                { label: "OS", value: "iOS" },
                { label: "OS Version", value: "15.7" },
                { label: "Device Model", value: "iPhone" },
                { label: "User Given Name", value: "None" },
                { label: "Device Last Location", value: "Country ISO: US\nLast Activity Time: 2025-02-20 21:58:55 UTC" }
              ]
            }
          ],
          unlinkedClusters: [
            {
              title: "iPhone (Generic)",
              norm_client: "Google Chrome",
              dateString: "Jan 21, 2025 – Feb 20, 2025",
              event_count: 16,
              query: "browser:chrome_ios"
            },
            {
              title: "iPhone (Generic)",
              norm_client: "Safari",
              dateString: "Jun 8, 2025 – Jun 12, 2025",
              event_count: 8,
              query: "browser:safari_ios"
            }
          ]
        }
      ];
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
.border-left {
  border-left: 1px solid #e0e0e0;
}
.w-100 {
  width: 100%;
}
.shadow-sm {
  box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.1);
}
.unlinked-activity-row {
  background-color: #fafafa;
  border: 1px dashed #bdbdbd !important;
  border-radius: 8px;
}
</style>
