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
  <v-card min-width="500px" class="mx-auto" max-width="500px" min-height="260px">
    <v-btn class="float-right mr-1 mt-1" icon @click="$emit('close')">
      <v-icon title="Close dialog">mdi-close</v-icon>
    </v-btn>
    <v-card-text>
      <strong>Quick tags</strong>
      <v-chip-group>
        <v-chip
          v-for="tag in quickTags"
          :key="tag.tag"
          :color="tag.color"
          :text-color="tag.textColor"
          :disabled="!!tagsAssignedToAll.includes(tag.tag)"
          class="text-center"
          small
          @click="addTags(tag.tag)"
          @click.stop="$emit('close')"
          title="Add quick tag"
        >
          <v-icon small left> {{ tag.label }} </v-icon>
          {{ tag.tag }}
        </v-chip>
      </v-chip-group>
      <strong>Assigned tags</strong>
      <v-chip-group column>
        <v-chip
          v-for="tag in assignedTags"
          :key="tag"
          :color="getQuickTag(tag) ? getQuickTag(tag).color : ''"
          :text-color="getQuickTag(tag) ? getQuickTag(tag).textColor : ''"
          class="text-center"
          small
          close
          @click:close="removeTags(tag)"
          title="Remove "
        >
          <v-icon v-if="getQuickTag(tag)" small left>{{ getQuickTag(tag).label }}</v-icon>
          {{ tag }}
        </v-chip>
      </v-chip-group>
      <br />
      <v-combobox
        v-model="selectedTags"
        :hide-no-data="!search"
        :items="customTags"
        :search-input.sync="search"
        hide-selected
        label="Add tags ..."
        small-chips
        outlined
        @change="addTags(selectedTags)"
      >
        <template v-slot:no-data>
          <v-list-item>
            <span class="subheading">Create new tag: </span>
            <v-chip
              class="ml-1"
              small
            >
              {{ search }}
            </v-chip>
          </v-list-item>
        </template>
        <template v-slot:item="{ item }">
          <v-chip
            small
          >
            {{ item }}
          </v-chip>
        </template>
      </v-combobox>
    </v-card-text>
  </v-card>
</template>

<script>
import DB from '@/database/index.js'

export default {
  props: {
    events: {
      type: Array,
      default: () => []
    },
    showPropagateOption: {
      type: Boolean,
      default: false
    },
    eventCount: {
      type: Number,
      default: 0
    },
    eventsQuery: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      listItems: [],
      selectedTags: null,
      propagateToEvents: false,
      // TODO: Refactor this into a configurable option
      quickTags: [
        { tag: 'bad', color: 'red', textColor: 'white', label: 'mdi-alert-circle-outline' },
        { tag: 'suspicious', color: 'orange', textColor: 'white', label: 'mdi-help-circle-outline' },
        { tag: 'good', color: 'green', textColor: 'white', label: 'mdi-check-circle-outline' },
      ],
      search: null,
    }
  },
  computed: {
    shouldShowCheckbox() {
      return this.showPropagateOption && this.eventCount > 0;
    },
    checkboxLabel() {
      if (this.eventCount === 1) return 'Apply tag to 1 matching event';
      return `Apply tag to all ${this.eventCount} matching events`;
    },
    project() {
      return this.$store.state.project
    },
    tags() {
      return this.$store.state.tags.map((tag) => tag.tag)
    },
    event() {
      return (this.events && this.events.length > 0) ? this.events[0] : null;
    },
    assignedTags() {
      let tags = new Set();
      if (this.events && Array.isArray(this.events)) {
        for (const event of this.events) {
          if (event && event._source && event._source.tags && Array.isArray(event._source.tags)) {
            event._source.tags.forEach(e => tags.add(e))
          }
        }
      }
      return [...tags];
    },
    tagsAssignedToAll() {
      if (!this.events || this.events.length === 0) return [];
      return this.quickTags.filter((el) =>
        this.events.every(ev => {
          const tags = (ev && ev._source && ev._source.tags) || []
          return tags.includes(el.tag)
        })
      ).map(t => t.tag);
    },
    customTags() {
      if (this.events && this.events.length > 0 && !this.events.every(ev => !ev || !ev._source || !ev._source.tags)) return []
      // returns all custom tags available for a sketch without the ones that are already applied to an event
      let customTags = this.tags.filter((tag) => !this.getQuickTag(tag))
      customTags = customTags.filter((tag) => !this.assignedTags.includes(tag))
      customTags.sort((a, b) => { return a.localeCompare(b)})
      return customTags
    },
  },
  methods: {
    getQuickTag(tag) {
      return this.quickTags.find((el) => el.tag === tag)
    },
    async removeTags(tag) {
      if (this.events && this.events.length > 0) {
        for (const event of this.events) {
          if (event && event._source && event._source.tags) {
            const newTags = event._source.tags.filter(t => t !== tag)
            if (newTags.length !== event._source.tags.length) {
              await DB.updateEventTags(event._id, newTags)
              event._source.tags = newTags
            }
          }
        }
      }
      this.$store.dispatch('updateEventLabels', { label: tag, num: -1 })
      this.$emit('tag-removed', tag)
    },
    async addTags(tagToAdd) {
      if (!tagToAdd) return
      
      const tagList = Array.isArray(tagToAdd) ? tagToAdd : [tagToAdd]
      
      if (this.events && this.events.length > 0) {
        for (const event of this.events) {
          if (!event) continue;
          const source = event._source || {}
          const currentTags = source.tags || []
          // Merge unique
          const newTags = [...new Set([...currentTags, ...tagList])]
          try {
            await DB.updateEventTags(event._id, newTags)
            // Update local state
            if (!event._source) event._source = {}
            event._source.tags = newTags
          } catch (e) {
            console.error(e)
          }
        }
      }

      this.$emit('close')
      this.$emit('tag-added', tagList[0])
      this.$store.dispatch('updateEventLabels', { label: tagList[0], num: 1 })
      
      if (this.$store.state.demoMode) {
        const EventBus = require('@/event-bus.js').default
        EventBus.$emit('demo:action', 'tag-added')
      }

      this.$nextTick(() => {
        this.selectedTags = null
        this.search = null
      })
    },
  },
}
</script>

<style scoped lang="scss"></style>
