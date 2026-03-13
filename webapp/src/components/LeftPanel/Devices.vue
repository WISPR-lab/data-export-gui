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
    <v-icon :color="isActive ? 'primary' : ''">mdi-devices</v-icon>
  </div>
  <div v-else>
    <v-divider class="mb-0"></v-divider>
    <div
      class="pa-4"
      style="cursor: pointer"
      @click="navigateToDevices"
      :class="[
        $vuetify.theme.dark ? 'dark-hover' : 'light-hover',
        isActive ? 'active-view' : ''
      ]"
    >
      <span> <v-icon left :color="isActive ? 'primary' : ''">mdi-devices</v-icon> Devices </span>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    iconOnly: Boolean,
  },
  computed: {
    isActive() {
      return this.$route.name === 'Devices'
    }
  },
  methods: {
    navigateToDevices() {
      if (this.$route.path !== '/devices') {
        this.$router.push('/devices')
      }
    },
  },
}
</script>

<style scoped lang="scss">
.active-view {
  background-color: rgba(25, 118, 210, 0.05);
  font-weight: 500;
}
</style>

<style scoped lang="scss">
.dark-hover:hover {
  background-color: rgba(255, 255, 255, 0.08);
}

.light-hover:hover {
  background-color: rgba(0, 0, 0, 0.04);
}
</style>
