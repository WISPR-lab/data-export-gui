<!--
Copyright 2025 Google Inc. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

<template>
  <div
    v-if="iconOnly"
    class="pa-4"
    style="cursor: pointer"
    @click="
      $emit('toggleDrawer')
      expanded = true
    "
  >
    <v-icon left>mdi-ip</v-icon>
    <div style="height: 1px"></div>
  </div>
  <div v-else>
    <div
      :style="ipAddresses && ipAddresses.length ? 'cursor: pointer' : ''"
      class="pa-4"
      @click="expanded = !expanded"
      :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'"
    >
      <span> <v-icon left>mdi-ip</v-icon>IP Addresses</span>
      <span class="float-right" style="margin-right: 10px">
        <small v-if="ipAddresses"
          ><strong>{{ ipAddresses.length }}</strong></small
        >
      </span>
    </div>

    <v-expand-transition>
      <div v-show="expanded && ipAddresses.length" class="pl-8 pr-4 pb-4">
        <ts-i-p-addresses-list></ts-i-p-addresses-list>
      </div>
    </v-expand-transition>
    <v-divider></v-divider>
  </div>
</template>

<script>
import TsIPAddressesList from './IPAddressesList.vue'
import DB from '@/database/index.js'

export default {
  props: {
    iconOnly: Boolean,
  },
  components: {
    TsIPAddressesList,
  },
  data: function () {
    return {
      expanded: false,
      ipAddresses: [],
    }
  },
  computed: {
    sketch() {
      return this.$store.state.sketch
    },
  },
  async mounted() {
    try {
      this.ipAddresses = await DB.getIPAddresses();
    } catch (e) {
      console.error('Error loading IP addresses:', e)
      this.ipAddresses = []
    }
  },
}
</script>

<style scoped lang="scss"></style>
