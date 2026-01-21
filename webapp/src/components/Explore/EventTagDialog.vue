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
import BrowserDB from '../../database.js'

export default {
  props: ['events'],
  data() {
    return {
      listItems: [],
      selectedTags: null,
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
    sketch() {
      return this.$store.state.sketch
    },
    tags() {
      return this.$store.state.tags.map((tag) => tag.tag)
    },
    event() {
      return this.events[0];
    },
    assignedTags() {
      let tags = new Set();
      for (const event of this.events) {
        if (event._source.tags && Array.isArray(event._source.tags)) {
          event._source.tags.forEach(e => tags.add(e))
        }
      }
      return [...tags];
    },
    tagsAssignedToAll() {
      return this.quickTags.filter((el) =>
        this.events.every(ev => {
          const tags = ev._source.tags || []
          return tags.includes(el.tag)
        })
      ).map(t => t.tag);
    },
    customTags() {
      if (!this.events.every(ev => !ev._source.tag)) return []
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
    removeTags(tag) {
      // Extract event IDs from the _id field in event objects
      const eventIds = this.events.map(ev => ev._id);
      
      BrowserDB.untagEvent(eventIds, [tag])
        .then((response) => {
          // Update in-memory event objects to reflect DB change
          for (let event of this.events) {
            if (event._source.tags) {
              const index = event._source.tags.indexOf(tag);
              if (index !== -1) {
                event._source.tags.splice(index, 1);
              }
            }
          }
          this.$store.dispatch('updateTimelineTags', { sketchId: this.sketch.id, tag: tag, num: -1 })
        })
        .catch((e) => {
          console.error('Error removing tag:', e)
        })
    },
    addTags: function (tagToAdd) {
      // Ensure all events have tags array
      for (let event of this.events) {
        if (!event._source.hasOwnProperty('tags')) {
          this.$set(event._source, 'tags', [])
        }
      }
      
      // Only tag events that don't already have this tag
      const eventsWithoutTag = this.events.filter((ev) =>
        !(ev._source.tags && ev._source.tags.includes(tagToAdd))
      );
      
      if (eventsWithoutTag.length === 0) return; // Nothing to do

      // Extract event IDs
      const eventIds = eventsWithoutTag.map(ev => ev._id);

      BrowserDB.tagEvent(eventIds, [tagToAdd])
        .then((response) => {
          // Update in-memory event objects to reflect DB change
          for (let event of eventsWithoutTag) {
            if (!event._source.tags.includes(tagToAdd)) {
              event._source.tags.push(tagToAdd);
            }
          }
          this.$store.dispatch('updateTimelineTags', { sketchId: this.sketch.id, tag: tagToAdd, num: 1 })
        })
        .catch((e) => {
          console.error('Cannot tag event! Error:', e)
        })
      
      this.$nextTick(() => {
        this.selectedTags = null
        this.search = null
      })
    },
  },
}
</script>

<style scoped lang="scss"></style>
