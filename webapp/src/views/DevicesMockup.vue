// added for WISPR-lab/data-export-gui
<template>
  <v-container class="pa-6 white min-h-100" style="max-width: 1100px;">

    <!-- <h1 class="text-h4 text--primary mb-6">Devices</h1>
    
    <p class="text-body-2 text--primary" style="line-height: 1.7;">
      Data exports often contain information about currently logged-in devices in addition to lists of login events associated with some information about the origin device. 
      LEStrADE attempts to unify this data using a two-level abstraction:
    </p>

    <ul class="text-body-2 text--primary mb-6" style="line-height: 1.7;">
      <li class="mb-1">
        <strong>Device Instance</strong>: A group of one or more raw records mapping to a trusted/registered device (e.g., for 2FA) or a group of login events linked by a common identifier (e.g., session ID or serial number) or tracked across browser/app upgrades.
      </li>
      <li>
        <strong>Device Profile</strong>: A super-group of one or more <strong>device instances</strong> that share the same hardware model (e.g., Apple iPhone 11).
      </li>
    </ul> -->

    <!-- Generic Platform Loop -->
    <v-card 
      v-for="(platform, pIdx) in groupedPlatforms"
      :key="'platform-' + pIdx"
      outlined 
      class="pa-5 rounded-xl mb-5 shadow-sm" 
      style="background-color: white;"
    >
      <!-- Platform Header -->
      <div class="d-flex align-center mb-4">
        <v-avatar size="44" :color="platform.color" class="mr-3">
          <v-icon color="white" size="26">{{ platform.icon }}</v-icon>
        </v-avatar>
        <div>
          <h2 class="text-h6 text--primary font-weight-medium mb-0">{{ platform.displayName }} Account</h2>
          <div class="text-body-2 text--secondary">{{ platform.accountLabel }}</div>
        </div>
      </div>

      <!-- Platform Sections Loop -->
      <div 
        v-for="(section, sIdx) in platform.sections"
        :key="'section-' + sIdx"
        :class="sIdx > 0 ? 'mt-6 border-top pt-4' : ''"
      >
        <h3 class="text-subtitle-1 text--primary font-weight-medium mb-3">
          {{ section.title }}
        </h3>

        <!-- Standard Panel List for Entries -->
        <v-expansion-panels flat class="device-panels">
          <v-expansion-panel
            v-for="(entry, eIdx) in section.entries"
            :key="'entry-' + eIdx"
            class="mb-3 border rounded-xl overflow-hidden device-profile-card"
          >
            <v-expansion-panel-header class="pa-4">
              <template v-slot:default="{ open }">
                <div class="device-header-row py-1 d-flex align-center justify-space-between w-100">
                  <!-- Left: Icon & Identity/Telemetry text blocks -->
                  <div class="d-flex align-start flex-grow-1">
                    <v-avatar size="44" color="grey lighten-4" class="mr-5 flex-shrink-0">
                      <v-icon color="grey darken-3" size="22">{{ entry.icon }}</v-icon>
                    </v-avatar>
                    
                    <div class="d-flex flex-column">
                      <!-- Row 1: Identity Pair -->
                      <div class="d-flex flex-wrap align-baseline">
                        <span class="text-subtitle-1 text--primary font-weight-medium">
                          {{ entry.title }}
                        </span>
                        <span v-if="entry.norm_client" class="text-body-2 text--secondary font-weight-regular ml-2">
                          via {{ entry.norm_client }}
                        </span>
                      </div>
                      
                      <!-- Row 2: Telemetry Pair (Responsive Date & Location) -->
                      <div v-if="entry.dateString || entry.location" class="d-flex flex-wrap align-center text-body-2 text--secondary mt-0.5">
                        <span v-if="entry.dateString">{{ entry.dateString }}</span>
                        <span v-if="entry.dateString && entry.location" class="mx-2 d-none d-sm-inline">•</span>
                        <span v-if="entry.location" class="d-flex align-center">
                          <v-icon size="14" class="mr-1 grey--text text--darken-1">mdi-map-marker-outline</v-icon>
                          {{ entry.location }}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Right Side: strictly right-aligned chips only -->
                  <div class="text-right mr-4 flex-shrink-0 d-flex align-center justify-end" style="gap: 12px;">
                    <!-- Fingerprint Chip (with standard hover tooltip) -->
                    <v-tooltip v-if="entry.is_reduced_ua" bottom max-width="320">
                      <template v-slot:activator="{ on, attrs }">
                        <v-chip
                          small
                          color="grey lighten-2"
                          class="font-weight-medium flex-shrink-0 grey--text text--darken-3"
                          v-bind="attrs"
                          v-on="on"
                        >
                          <v-icon left small class="grey--text text--darken-3">mdi-fingerprint-off</v-icon>
                          Reduced User-Agent
                        </v-chip>
                      </template>
                      <span>To prevent fingerprinting, browsers on iPhones use generic User-Agents that hide the exact model.</span>
                    </v-tooltip>

                    <!-- Cookie Badge Chip -->
                    <v-chip 
                      v-if="entry.augmented_from_recognized" 
                      small 
                      color="primary" 
                      outlined
                    >
                      Trusted Cookie
                    </v-chip>

                    <!-- Event Count Action Link -->
                    <v-btn
                      v-if="entry.event_count"
                      text
                      small
                      color="primary"
                      class="text-capitalize ml-2"
                      @click.stop="goToEventsPage(entry)"
                    >
                      {{ entry.event_count }} Events
                      <v-icon right small>mdi-arrow-right</v-icon>
                    </v-btn>
                  </div>
                </div>
              </template>
            </v-expansion-panel-header>

            <v-expansion-panel-content class="grey lighten-5 border-top">
              <div class="pa-4">
                <div class="text-body-2 text--primary font-weight-medium mb-3">
                  {{ getDetailsTitle(entry.entity_type) }}
                </div>
                <attributes-table :attributes="entry.formatted_attributes" />
              </div>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </div>
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
  computed: {
    groupedPlatforms() {
      const self = this;
      return this.platforms.map(function(platform) {
        const groups = {};
        
        // Group entries by entity_type
        platform.entries.forEach(function(entry) {
          const type = entry.entity_type || 'session';
          if (!groups[type]) {
            groups[type] = [];
          }
          groups[type].push(entry);
        });

        // Map entity_type to standard section definitions
        const sections = Object.keys(groups).map(function(type) {
          return {
            entity_type: type,
            title: self.getSectionTitle(type),
            description: self.getSectionDescription(type),
            entries: groups[type]
          };
        });

        return {
          displayName: platform.displayName,
          accountLabel: platform.accountLabel,
          icon: platform.icon,
          color: platform.color,
          sections: sections
        };
      });
    }
  },

  mounted() {
    this.fetchMockData();
  },
  methods: {
    getSectionTitle(type) {
      const titles = {
        'session': 'Sessions',
        'app_registration': 'App Registrations',
        'hardware_registration': 'Hardware Registrations',
        'trusted_cookie': 'Trusted Cookies',
        'platform_inferred_device': 'Platform Inferred Devices'
      };
      return titles[type] || 'Other Connection Records';
    },
    getSectionDescription(type) {
      const descriptions = {
        'session': 'Account access sessions recorded by this platform.',
        'app_registration': 'Native applications registered on this account.',
        'hardware_registration': 'Physical devices registered with this account.',
        'trusted_cookie': 'Browser sessions remembered by this platform.',
        'platform_inferred_device': 'Devices inferred by the platform based on activity logs.'
      };
      return descriptions[type] || '';
    },
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
    goToEventsPage(entry) {
      if (this.$router) {
        const routeName = this.$route.name === 'DemoDevices' ? 'DemoEvents' : 'Events';
        this.$router.push({
          name: routeName,
          query: { q: `device_profiles_data:${entry.title}` }
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
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphonexr-session" },
                { label: "Model", value: "Apple iPhone XR" },
                { label: "OS", value: "iOS 17.7.1" },
                { label: "IP Addresses", value: ["2600:6c44:11f0:f010:44b8:b949:c7eb:7f04", "144.92.239.37"] },
                { label: "Client Session Id", value: "Nvt2********************" },
                { label: "User Agent Original", value: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/21H216 [FBAN/FBIOS;FBAV/492.0.0.101.111;FBBV/670308045;FBDV/iPhone11,8;FBMD/iPhone;FBSN/iOS;FBSV/17.7.1;FBSS/0;FBID/phone;FBLC/en_US;FBOP/5]" },
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
              event_count: 5,
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
              event_count: 8,
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
              formatted_attributes: [
                { label: "Instance ID", value: "inst-fb-iphone7-alice-session" },
                { label: "Model", value: "Apple iPhone 7" },
                { label: "OS", value: "iOS 15.7" },
                { label: "IP Addresses", value: ["72.33.2.108"] },
                { label: "Client Session Id", value: "VvKP********************" },
                { label: "User Agent Original", value: "Mozilla/5.0 (iPhone; CPU iPhone OS 15_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/19H12 [FBAN/FBIOS;FBDV/iPhone9,3;FBMD/iPhone;FBSN/iOS;FBSV/15.7;FBSS/2;FBID/phone;FBLC/en_US;FBOP/5]" },
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
          ]
        }
      ];
    },
    formatDate(ts) {
      if (!ts) return '';
      return new Date(ts * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
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
.w-100 {
  width: 100%;
}
.shadow-sm {
  box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.1);
}
</style>
