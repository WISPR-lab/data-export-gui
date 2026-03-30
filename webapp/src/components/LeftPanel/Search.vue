<!--
Copyright 2023 Google Inc. All rights reserved.

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
    @click="navigateToExplore"
  >
    <v-icon :color="isActive ? 'primary' : ''">mdi-magnify</v-icon>
  </div>

  <div v-else>
    <v-divider class="mb-0"></v-divider>
    <div
      class="pa-4"
      style="cursor: pointer"
      @click="navigateToExplore"
      :class="[
        $vuetify.theme.dark ? 'dark-hover' : 'light-hover',
        isActive ? 'active-view' : ''
      ]"
    >
      <span> <v-icon left :color="isActive ? 'primary' : ''">mdi-magnify</v-icon> Events </span>
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
      return this.$route.name === 'Explore'
    }
  },
  methods: {
    navigateToExplore() {
      if (this.$route.path !== '/explore') {
        this.$router.push('/explore')
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

