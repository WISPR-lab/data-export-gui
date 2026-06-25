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

<!--  NOTICE --- MODIFIED FOR WISPR-lab/data-export-gui -->
  
<template>
  <div>
    <h3>Rename project</h3>
    <br />
    <v-form @submit.prevent="renameSketch()">
      <v-text-field
        outlined
        dense
        autofocus
        v-model="newProjectName"
        @focus="$event.target.select()"
        clearable
        counter="50"
        :rules="projectNameRules"
      >
      </v-text-field>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn text @click="closeDialog()"> Cancel </v-btn>
        <v-btn :disabled="!newProjectName || newProjectName.length > 50" text color="primary" @click="renameSketch()">
          Save
        </v-btn>
      </v-card-actions>
    </v-form>
  </div>
</template>

<script>
export default {
  props: ['projectId'],
  data() {
    return {
      newProjectName: '',
      projectNameRules: [
        (v) => !!v || 'Project name is required.',
        (v) => (v && v.length <= 50) || 'Project name is too long.',
      ],
    }
  },
  computed: {
    project() {
      return this.$store.state.project
    },
  },
  methods: {
    renameSketch() {
      // Update virtual sketch name in localStorage
      localStorage.setItem('projectName', this.newProjectName)
      
      // Update Vuex state
      const updatedProject = { ...this.project, name: this.newProjectName }
      this.$store.commit('SET_PROJECT', { 
        objects: [updatedProject], 
        meta: this.$store.state.meta 
      })
      
      this.$emit('close')
    },
    closeDialog: function () {
      this.newProjectName = this.project.name
      this.$emit('close')
    },
  },
  created() {
    this.newProjectName = this.project.name
  },
}
</script>

<!-- CSS scoped to this component only -->
<style scoped lang="scss"></style>
