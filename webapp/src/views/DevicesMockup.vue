// added for WISPR-lab/data-export-gui
<template>
  <v-container class="pa-6 white min-h-100" style="max-width: 1400px;">
    <div class="mb-6">
      <h1 class="text-h4 font-weight-bold text--primary mb-1">Devices (Mockup)</h1>
      <div class="text-body-2 text--secondary">Track account access records and detected device activity.</div>
    </div>

    <platform-card
      v-for="(platform, idx) in platforms"
      :key="'platform-' + idx"
      :platform="platform"
      :page-size="PAGE_SIZE"
      @update:clusterPage="platform.clusterPage = $event"
    />
  </v-container>
</template>

<script>
import PlatformCard from '@/components/Devices_v2/PlatformCard.vue';
import { getResolvedSessionsRegistrations } from '@/database/queries/resolved_sessions_registrations.js';
import { getUnlinkedClusters } from '@/database/queries/instances_v2.js';
import { getDB } from '@/database/index.js';
import { hexColor } from '@/utils/hex.js';
import { getUASummary } from '@/database/queries/ua_summary.js';

// display-only defaults when a platform key is unrecognized.
var PLATFORM_META = {
  facebook:  { displayName: 'Facebook',    icon: 'mdi-facebook',  color: '#5E75C2' },
  google:    { displayName: 'Google',       icon: 'mdi-google',    color: '#FD7EAC' },
  apple:     { displayName: 'Apple/iCloud', icon: 'mdi-apple',     color: '#000000' },
  discord:   { displayName: 'Discord',      icon: 'mdi-discord',   color: '#5865F2' },
  instagram: { displayName: 'Instagram',    icon: 'mdi-instagram', color: '#E1306C' }
};

// OS/device-type icon — keyed off os fields first, entity type as last resort
function osIcon(s) {
  var os    = ((s.os_name || '') + ' ' + (s.os_type || '')).toLowerCase();
  var model = (s.model_name || '').toLowerCase();
  if (os.indexOf('ios') !== -1 || os.indexOf('iphone') !== -1 || model.indexOf('iphone') !== -1) return 'mdi-apple-ios';
  if (os.indexOf('mac') !== -1 || model.indexOf('mac') !== -1)  return 'mdi-laptop-mac';
  if (os.indexOf('android') !== -1)  return 'mdi-android';
  if (os.indexOf('windows') !== -1)  return 'mdi-microsoft-windows';
  if (os.indexOf('linux') !== -1)    return 'mdi-linux';
  var entityFallback = {
    app_registration:         'mdi-cellphone-link',
    hardware_registration:    'mdi-cellphone',
    platform_inferred_device: 'mdi-check-decagram-outline',
    session:                  'mdi-devices'
  };
  return entityFallback[s.entity_type] || 'mdi-devices';
}

var SECTION_DEFS = [
  {
    key: 'session',
    label: 'Sessions',
    description: 'Each entry is one recorded login. Many platforms assign a unique ID per session, so the same phone or laptop can appear multiple times if you\'ve logged in and out.',
    detailLabel: 'Details',
    sortByGroup: true
  },
  {
    key: 'app_registration',
    label: 'App Installs',
    description: 'Records of individual app installations registered with this platform. Each install of the app on a device gets its own unique ID — used for push notifications and device-level tracking. A single phone with both the main app and a secondary app would appear as two separate entries.',
    detailLabel: 'Details',
    sortByGroup: false
  },
  {
    key: 'hardware_registration',
    label: 'OS-Linked Devices',
    description: 'Physical devices connected to this account at the operating system level — like a phone signed in through its system account settings. These often include hardware identifiers like serial numbers or IMEIs.',
    detailLabel: 'Details',
    sortByGroup: false
  },
  {
    key: 'platform_inferred_device',
    label: 'Devices Identified by This Platform',
    description: 'Devices this platform directly recognizes using their own methods — persistent cookies, hardware IDs, or server-side fingerprinting. More reliable than our own analysis since they have access to signals we don\'t.',
    detailLabel: 'Attributes',
    sortByGroup: false
  }
];

var TIMESTAMP_KEYS = ['entity_first_seen_timestamp', 'entity_last_seen_timestamp', 'timestamp'];

function buildEntry(s) {
  var attrs = s.attributes;
  var firstSeen = attrs.entity_first_seen_timestamp || null;
  var lastSeen  = attrs.entity_last_seen_timestamp  || null;
  var location  = attrs.location || attrs.device_last_location || '';

  var formattedAttrs = Object.entries(attrs)
    .filter(function(pair) { return !pair[0].startsWith('norm__') && pair[1] !== null && pair[1] !== ''; })
    .map(function(pair) {
      var k = pair[0]; var v = pair[1];
      return {
        label: k.replace(/_/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); }),
        value: typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v),
        isTimestamp: TIMESTAMP_KEYS.indexOf(k) !== -1
      };
    });

  var summary = getUASummary([s])[0] || {};
  var clientLabel = summary.primary ? (summary.primary + (summary.secondary ? ' (' + summary.secondary + ')' : '')) : s.client_name;

  return {
    id: s.id,
    entity_type: s.entity_type,
    instance_id: s.instance_id || null,
    title: s.model_name,
    client_name: clientLabel,
    icon: osIcon(s),
    firstSeen: firstSeen,
    lastSeen: lastSeen,
    location: location,
    is_reduced_ua: s.is_reduced_ua,
    has_trusted_cookie: s.has_trusted_cookie,
    has_passkey: s.has_passkey,
    event_count: s.event_count,
    events_query: s.events_query,
    formatted_attributes: formattedAttrs
  };
}

function sortByGroup(entries) {
  var instMax = {};
  entries.forEach(function(e) {
    if (!e.instance_id) return;
    if (!instMax[e.instance_id] || e.lastSeen > instMax[e.instance_id]) {
      instMax[e.instance_id] = e.lastSeen || '';
    }
  });
  return entries.slice().sort(function(a, b) {
    var aKey = a.instance_id ? (instMax[a.instance_id] || '') : (a.lastSeen || '');
    var bKey = b.instance_id ? (instMax[b.instance_id] || '') : (b.lastSeen || '');
    if (aKey !== bKey) return aKey < bKey ? 1 : -1;
    var aL = a.lastSeen || ''; var bL = b.lastSeen || '';
    return aL < bL ? 1 : aL > bL ? -1 : 0;
  });
}

function sortByLastSeen(entries) {
  return entries.slice().sort(function(a, b) {
    var aL = a.lastSeen || ''; var bL = b.lastSeen || '';
    if (!aL && !bL) return 0;
    if (!aL) return 1;
    if (!bL) return -1;
    return aL < bL ? 1 : aL > bL ? -1 : 0;
  });
}

function buildSection(def, uploadEntries) {
  var entries = uploadEntries.filter(function(e) { return e.entity_type === def.key; });
  entries = def.sortByGroup ? sortByGroup(entries) : sortByLastSeen(entries);
  return { key: def.key, label: def.label, description: def.description, detailLabel: def.detailLabel, entries: entries, page: 1 };
}

export default {
  name: 'DevicesMockup',
  components: { PlatformCard },
  data() {
    return {
      platforms: [],
      PAGE_SIZE: 5
    };
  },
  mounted() {
    this.fetchLiveData();
  },
  methods: {
    async fetchLiveData() {
      try {
        var db = await getDB();
        var uploads = await db.exec('SELECT * FROM uploads', { returnValue: 'resultRows', rowMode: 'object' });
        var states = await getResolvedSessionsRegistrations();
        var allClusters = await getUnlinkedClusters();

        this.platforms = uploads.map(function(upload) {
          var key = (upload.platform || '').toLowerCase();
          var meta = PLATFORM_META[key] || { displayName: upload.platform || 'Unknown', icon: 'mdi-account', color: '#757575' };
          var dbColor = upload.color ? hexColor(upload.color) : null;

          var uploadEntries = states
            .filter(function(s) { return s.upload_id === upload.id; })
            .map(buildEntry);

          var sections = SECTION_DEFS.map(function(def) { return buildSection(def, uploadEntries); });
          var totalGroundTruth = sections.reduce(function(sum, s) { return sum + s.entries.length; }, 0);
          var clusters = allClusters.filter(function(c) { return c.upload_id === upload.id; });

          return {
            displayName: meta.displayName,
            accountLabel: upload.given_name || 'Primary Account',
            icon: meta.icon,
            color: dbColor || meta.color,
            sections: sections,
            totalGroundTruth: totalGroundTruth,
            clusters: clusters,
            clusterPage: 1
          };
        });

      } catch (err) {
        console.error('Error fetching live DB data for mockup:', err);
      }
    }
  }
};
</script>

<style scoped>
.min-h-100 { min-height: 100vh; }
</style>
