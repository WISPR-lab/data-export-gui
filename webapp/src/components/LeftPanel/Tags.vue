<!--
Copyright 2022 Google Inc. All rights reserved.

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

<!--NOTICE --- MODIFIED FOR WISPR-lab/data-export-gui -->


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
    <v-icon left>mdi-tag-multiple-outline</v-icon>
    <div style="height: 1px"></div>
  </div>
  <div v-else id="tsLeftPanelTags">
    <div
      :style="(tags && tags.length) || (filteredLabels && filteredLabels.length) ? 'cursor: pointer' : ''"
      class="pa-4"
      @click="expanded = !expanded"
      :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'"
    >
      <span> <v-icon left>mdi-tag-multiple-outline</v-icon> Tags & Stars </span>

      <span class="float-right" style="margin-right: 10px">
        <small v-if="tags && filteredLabels">
          <strong>{{ filteredCount !== null ? filteredCount : totalTagsCount }}</strong>
        </small>
      </span>
    </div>

    <v-expand-transition>
      <div v-show="expanded && ((tags || []).length || (filteredLabels || []).length)">
        <tags-list @filtered-count="filteredCount = $event"></tags-list>
      </div>
    </v-expand-transition>
    <v-divider></v-divider>
  </div>
</template>

<script>
import TagsList from './TagsList.vue'

export default {
  props: {
    iconOnly: Boolean,
  },
  components: {
    TagsList,
  },
  data: function () {
    return {
      expanded: false,
      filteredCount: null,
    }
  },
  computed: {
    project() {
      return this.$store.state.project
    },
    meta() {
      return this.$store.state.meta
    },
    tags() {
      return this.$store.state.tags
    },
    filteredLabels() {
      if (!this.meta.filter_labels) return []
      return this.meta.filter_labels.filter(function (label) {
        const name = label.tag || label.label
        return label && typeof name === 'string' && !name.startsWith('__ts_fact')
      })
    },
    totalTagsCount() {
      return (this.tags || []).length + (this.filteredLabels || []).length
    }
  },
}
</script>
