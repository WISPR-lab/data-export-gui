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
    @click="navigateToDevices"
  >
    <v-icon left>mdi-devices</v-icon>
    <div style="height: 1px"></div>
  </div>
  <div v-else>
    <div
      style="cursor: pointer"
      class="pa-4"
      @click="navigateToDevices"
      :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'"
    >
      <span> <v-icon left>mdi-devices</v-icon> Devices </span>
    </div>
    <v-divider></v-divider>
  </div>
</template>

<script>
export default {
  props: {
    iconOnly: Boolean,
  },
  methods: {
    navigateToDevices() {
      this.$router.push('/explore/devices')
    },
  },
}
</script>

<style scoped lang="scss">
.dark-hover:hover {
  background-color: rgba(255, 255, 255, 0.08);
}

.light-hover:hover {
  background-color: rgba(0, 0, 0, 0.04);
}
</style>
