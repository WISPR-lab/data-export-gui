<template>
  <div>
    <v-simple-table dense class="elevation-0 transparent">
      <template v-slot:default>
        <tbody>
          <tr v-for="attr in attributes" :key="attr.label" v-if="hasValidValue(attr)">
            <td class="text-body-2 font-weight-medium text--primary text-left" style="width: 200px; border-bottom: none !important;">
              {{ attr.label }}
            </td>
            <td class="text-body-2 text--primary text-left" style="word-break: break-word; border-bottom: none !important; padding-top: 4px; padding-bottom: 4px;">
              <span v-for="(item, idx) in getDisplayValue(attr)" :key="idx" class="d-inline-block">
                <template v-if="isIPAttribute(attr.label)">
                  <v-tooltip bottom open-delay="400">
                    <template v-slot:activator="{ on, attrs }">
                      <a 
                        v-bind="attrs" 
                        v-on="on" 
                        class="ip-link" 
                        @click.stop="goToExploreIP(item)"
                      >
                        {{ item }}
                      </a>
                    </template>
                    <span>See events with this IP address</span>
                  </v-tooltip>
                </template>
                <span v-else-if="attr.isTimestamp">{{ item | longDateTimeLocal }}</span>
                <span v-else>{{ item | formatDeviceDetails }}</span>
                <span v-if="idx < getDisplayValue(attr).length - 1" style="margin-right: 6px;">,</span>
              </span>
              <template v-if="hasSeeMore(attr)">
                <span class="mr-1">...</span>
                <a @click.stop="showAllItems(attr)" class="text-caption text-decoration-underline mb-1">
                  See all ({{ attr.value.length }})
                </a>
              </template>
            </td>
          </tr>
        </tbody>
      </template>
    </v-simple-table>

    <!-- Dialog for displaying all items (IPs or OS versions) -->
    <v-dialog v-model="detailModalOpen" max-width="500px" @click.native.stop>
      <v-card class="pa-4">
        <v-card-title class="text-h6 font-weight-bold px-0 pt-0 d-flex justify-space-between align-center">
          {{ modalTitle }}
          <v-btn icon small @click="detailModalOpen = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text class="px-0 py-2">
          <div class="d-flex flex-wrap" style="gap: 12px 16px;">
            <template v-if="isIPModal">
              <a 
                v-for="ip in modalItems" 
                :key="ip" 
                @click.stop="clickIPFromModal(ip)"
                class="ip-link"
                style="font-size: 14px;"
              >
                {{ ip }}
              </a>
            </template>
            <template v-else>
              <span 
                v-for="item in modalItems" 
                :key="item"
                style="font-size: 14px;"
                class="text-body-2 text--primary"
              >
                {{ item }}
              </span>
            </template>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
export default {
  name: 'AttributesTable',
  props: {
    attributes: {
      type: Array,
      required: true
    }
  },
  data() {
    return {
      detailModalOpen: false,
      modalTitle: '',
      modalItems: [],
      isIPModal: false
    };
  },
  computed: {
    MAX_OS_TYPES() {
      return 5;
    },
    MAX_IP_ADDRESSES() {
      return 5;
    }
  },
  methods: {
    goToExploreIP(ip) {
      const queryString = `client_ip:"${ip}"`;
      const routeName = this.$route.name === 'DemoDevices' ? 'DemoExplore' : 'Explore';
      this.$router.push({
        name: routeName,
        query: { q: queryString }
      });
    },
    isIPAttribute(label) {
      return label && /\bips?\b/i.test(label);
    },
    isOSAttribute(label) {
      return label && /\bos\b/i.test(label);
    },
    getLimit(label) {
      if (this.isIPAttribute(label)) return this.MAX_IP_ADDRESSES;
      if (this.isOSAttribute(label)) return this.MAX_OS_TYPES;
      return null;
    },
    hasValidValue(attr) {
      if (attr.value === null || attr.value === undefined) return false;
      if (Array.isArray(attr.value)) {
        return attr.value.length > 0;
      }
      const valStr = String(attr.value).trim();
      const lower = valStr.toLowerCase();
      return valStr !== '' && lower !== 'null' && lower !== 'none' && lower !== 'unknown' && lower !== 'undefined' && valStr !== '[]';
    },
    getDisplayValue(attr) {
      if (Array.isArray(attr.value)) {
        const limit = this.getLimit(attr.label);
        if (limit && attr.value.length > limit) {
          return attr.value.slice(0, limit);
        }
        return attr.value;
      }
      return [attr.value];
    },
    hasSeeMore(attr) {
      if (!Array.isArray(attr.value)) return false;
      const limit = this.getLimit(attr.label);
      return limit && attr.value.length > limit;
    },
    showAllItems(attr) {
      this.modalItems = attr.value;
      this.isIPModal = this.isIPAttribute(attr.label);
      this.modalTitle = this.isIPModal ? 'All Associated IP Addresses' : 'All Associated OS Versions';
      this.detailModalOpen = true;
    },
    clickIPFromModal(ip) {
      this.detailModalOpen = false;
      this.goToExploreIP(ip);
    }
  }
}
</script>

<style scoped>
.ip-link {
  position: relative;
  text-decoration: none;
  color: #1976d2;
  transition: color 0.2s ease;
  display: inline-block;
}

.ip-link::after {
  content: '';
  position: absolute;
  width: 100%;
  transform: scaleX(0);
  height: 1.5px;
  bottom: -1px;
  left: 0;
  background-color: #1976d2;
  transform-origin: bottom right;
  transition: transform 0.25s ease-out;
}

.ip-link:hover {
  color: #1565c0;
}

.ip-link:hover::after {
  transform: scaleX(1);
  transform-origin: bottom left;
}
</style>
