<template>
  <v-simple-table dense class="elevation-0 transparent">
    <template v-slot:default>
      <tbody>
        <tr v-for="attr in attributes" :key="attr.label" v-if="hasValidValue(attr)">
          <td class="font-weight-medium text-left" style="width: 200px; border-bottom: none !important; color: #424242;">
            {{ attr.label }}
          </td>
          <td class="text-left" style="word-break: break-word; border-bottom: none !important;">
            <!-- Timestamp formatting -->
            <template v-if="attr.isTimestamp">
              {{ attr.value | longDateTimeLocal }}
            </template>

            <!-- Array list formatting (with commas) -->
            <template v-else-if="Array.isArray(attr.value)">
              <span v-for="(item, idx) in attr.value" :key="item">
                <template v-if="isIPAttribute(attr.label)">
                  <a @click.stop="goToExploreIP(item)">{{ item }}</a>
                </template>
                <template v-else>
                  {{ item | formatDeviceDetails }}
                </template>
                <span v-if="idx < attr.value.length - 1">, </span>
              </span>
            </template>

            <!-- Default String formatting -->
            <template v-else>
              {{ attr.value | formatDeviceDetails }}
            </template>
          </td>
        </tr>
      </tbody>
    </template>
  </v-simple-table>
</template>

<script>
export default {
  name: 'DeviceAttributesTable',
  props: {
    attributes: {
      type: Array,
      required: true
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
      return label && label.toLowerCase().indexOf('ip address') !== -1;
    },
    hasValidValue(attr) {
      if (attr.value === null || attr.value === undefined) return false;
      if (Array.isArray(attr.value)) {
        return attr.value.length > 0;
      }
      const valStr = String(attr.value).trim();
      const lower = valStr.toLowerCase();
      return valStr !== '' && lower !== 'null' && lower !== 'none' && lower !== 'unknown' && lower !== 'undefined' && valStr !== '[]';
    }
  }
}
</script>
