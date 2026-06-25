<!--
Copyright 2019 Google Inc. All rights reserved.

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


<!-- NOTICE --- MODIFIED FOR WISPR-lab/data-export-gui -->

<template>
  <div>
    <!-- First-time demo offer modal -->
    <welcome-dialog v-model="showFirstTimeModal" @skip="skipDemo" @start="startDemo"></welcome-dialog>

    <!-- Progress indicator when loading sketch data -->
    <v-progress-linear v-if="loadingProject" indeterminate color="primary"></v-progress-linear>

    <div v-if="project.id && !loadingProject" style="height: 70vh">
      <!-- Empty state -->
      <v-container v-if="!hasTimelines && !loadingProject && !isArchived" fill-height fluid>
        <v-row align="center" justify="center">
          <v-sheet class="pa-4" style="background: transparent">
            <center>
              <v-img src="./images/empty-state.png" max-height="100" max-width="300"></v-img>
              <div style="font-size: 2em" class="mb-3 mt-3">It's empty around here</div>
              <new-data-export-button btn-size="normal" btn-type="rounded"></new-data-export-button>
            </center>
          </v-sheet>
        </v-row>
      </v-container>


      <!-- Rename sketch dialog -->
      <v-dialog v-model="renameProjectDialog" width="600">
        <v-card class="pa-4">
          <ts-rename-sketch @close="renameProjectDialog = false"></ts-rename-sketch>
        </v-card>
      </v-dialog>

      <!-- Settings dialog -->
      <v-dialog v-model="showSettingsDialog" width="700px">
        <ts-settings-dialog></ts-settings-dialog>
      </v-dialog>



      <!-- Top horizontal toolbar -->
      <page-header
        v-if="!loadingProject"
        app
        clipped-left
        :show-drawer="hasTimelines && !loadingProject && !isArchived"
        @toggle-drawer="toggleDrawer()"
        @rename-project="renameProjectDialog = true"
      ></page-header>

      <!-- Left panel -->
      <v-navigation-drawer
        v-if="hasTimelines"
        v-model="showLeftPanel"
        app
        clipped
        disable-resize-watcher
        stateless
        hide-overlay
        :width="navigationDrawer.width"
      >
        <div id="tsMainViewsSection">
          <div class="pa-4 pb-0 overline grey--text text--darken-1" v-if="!isMiniDrawer">Views</div>
          
          <ts-search :icon-only="isMiniDrawer" @toggleDrawer="toggleDrawer()"></ts-search>
          <ts-devices :icon-only="isMiniDrawer" @toggleDrawer="toggleDrawer()"></ts-devices>
        </div>

        <v-divider v-if="!isMiniDrawer" class="mb-2"></v-divider>

        <div class="pa-4 pb-0 overline grey--text text--darken-1" v-if="!isMiniDrawer">Your Data</div>
        
        <v-divider v-if="!isMiniDrawer" class="mt-2"></v-divider>
        <ts-timelines-table :icon-only="isMiniDrawer" @toggleDrawer="toggleDrawer()"></ts-timelines-table>
        <ts-saved-searches
          v-if="meta && meta.views"
          :icon-only="isMiniDrawer"
          @toggleDrawer="toggleDrawer()"
        ></ts-saved-searches>
        <ts-data-types :icon-only="isMiniDrawer" @toggleDrawer="toggleDrawer()"></ts-data-types>
        <ts-i-p-addresses :icon-only="isMiniDrawer" @toggleDrawer="toggleDrawer()"></ts-i-p-addresses>
        <ts-tags :icon-only="isMiniDrawer" @toggleDrawer="toggleDrawer()"></ts-tags>
        <!-- <ts-search-templates :icon-only="isMiniDrawer" @toggleDrawer="toggleDrawer()"></ts-search-templates> -->
        
        
        <div class="pa-4">
          <new-data-export-button btnType="leftPanel"></new-data-export-button>
          <div class="pa-1"></div>
          <delete-data-button btnType="leftPanel"></delete-data-button>
        </div>
        
        <!-- <privacy-settings-item :icon-only="isMiniDrawer" @toggleDrawer="toggleDrawer()" @openSettings="showPrivacySettings = true"></privacy-settings-item> -->
      </v-navigation-drawer>

      <!-- Privacy Settings Modal -->
      <!-- <privacy-settings-modal v-model="showPrivacySettings"></privacy-settings-modal> -->

      <!-- Right panel -->
      <v-navigation-drawer v-if="showRightSidePanel" fixed right width="600" style="box-shadow: 0 10px 15px -3px #888">
        <template v-slot:prepend>
          <v-toolbar flat>
            <v-toolbar-title>Right Side Panel</v-toolbar-title>
            <v-spacer></v-spacer>
            <v-btn icon @click="showRightSidePanel = false">
              <v-icon title="Close sidepanel">mdi-close</v-icon>
            </v-btn>
          </v-toolbar>
        </template>
        <v-container> TODO: Add content here </v-container>
      </v-navigation-drawer>

      <!-- Main (canvas) view -->
      <v-main class="notransition">
        <!-- Scenario context -->
        <!--<ts-scenario-navigation v-if="project.status && hasTimelines && !isArchived"></ts-scenario-navigation>-->
        <!-- <ts-question-card
          v-if="
            project.status &&
            hasTimelines &&
            !isArchived &&
            systemSettings.DFIQ_ENABLED &&
            !questionCardExclusionRoutes.includes(currentRouteName)
          "
        ></ts-question-card> -->

        <router-view
          v-if="project.status && hasTimelines && !isArchived"
          @setTitle="(title) => (this.title = title)"
          class="mt-4"
        ></router-view>
      </v-main>

      <!-- Context search -->
      <v-bottom-sheet
        hide-overlay
        persistent
        no-click-animation
        v-model="showTimelineView"
        @click:outside="showTimelineView = false"
        scrollable
      >
        <v-card>
          <v-toolbar dense flat>
            <strong>Context search</strong>
            <v-btn-toggle v-model="contextTimeWindowSeconds" class="ml-10" rounded>
              <v-btn
                v-for="duration in [1, 5, 10, 60, 300, 600, 1800, 3600]"
                :key="duration"
                :value="duration"
                small
                outlined
                @click="updateContextQuery(duration)"
              >
                {{ duration | formatSeconds }}
              </v-btn>
            </v-btn-toggle>
            <v-btn small text class="ml-5" @click="contextToSearch()">Replace search</v-btn>

            <v-spacer></v-spacer>

            <v-btn icon :disabled="timelineViewHeight > 40" @click="increaseTimelineViewHeight()">
              <v-icon>mdi-chevron-up</v-icon>
            </v-btn>
            <v-btn icon :disabled="timelineViewHeight === 0" @click="decreaseTimelineViewHeight()">
              <v-icon>mdi-chevron-down</v-icon>
            </v-btn>
            <v-btn icon @click="showTimelineView = false">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </v-toolbar>
          <v-divider></v-divider>
          <v-expand-transition>
            <v-card-text :style="{ height: timelineViewHeight + 'vh' }" v-show="!minimizeTimelineView">
              <ts-event-list :query-request="queryRequest" :highlight-event="currentContextEvent"></ts-event-list>
            </v-card-text>
          </v-expand-transition>
        </v-card>
      </v-bottom-sheet>
    </div>
  </div>
</template>

<script>
import EventBus from '../event-bus.js'
import dayjs from '@/plugins/dayjs'
import DB from '../database/index.js'
import PageHeader from '../components/Navigation/PageHeader.vue'

import TsSavedSearches from '../components/LeftPanel/SavedSearches.vue'
import TsDataTypes from '../components/LeftPanel/DataTypes.vue'
import TsIPAddresses from '../components/LeftPanel/IPAddresses.vue'
import TsTags from '../components/LeftPanel/Tags.vue'
import TsSearchTemplates from '../components/LeftPanel/SearchTemplates.vue'
import TsSearch from '../components/LeftPanel/Search.vue'
import NewDataExportButton from '../components/Import/NewDataExportButton.vue'
import TsRenameSketch from '../components/RenameSketch.vue'
import TsEventList from '../components/Explore/EventList.vue'
import TsTimelinesTable from '../components/LeftPanel/TimelinesTable.vue'
import TsDevices from '../components/LeftPanel/Devices.vue'
import PrivacySettingsItem from '../components/LeftPanel/PrivacySettingsItem.vue'
import TsSettingsDialog from '../components/SettingsDialog.vue'
import DeleteDataButton from '../components/DeleteDataButton.vue'
import WelcomeDialog from '../components/Demo/WelcomeDialog.vue'

export default {
  props: ['projectId'],
  components: {
    PageHeader,
    TsSavedSearches,
    TsDataTypes,
    TsIPAddresses,
    TsTags,
    TsSearchTemplates,
    NewDataExportButton,
    TsRenameSketch,
    TsSearch,
    TsTimelinesTable,
    TsDevices,
    PrivacySettingsItem,
    TsEventList,
    TsSettingsDialog,
    DeleteDataButton,
    WelcomeDialog,
  },
  data() {
    return {
      showProjectMetadata: false,
      navigationDrawer: {
        width: 350,
      },
      isMiniDrawer: false,
      selectedScenario: null,
      scenarioDialog: false,
      showLeftPanel: true,
      leftPanelTab: 0,
      leftPanelTabItems: ['EXPLORE', 'INVESTIGATE'],
      renameProjectDialog: false,
      showHidden: false,
      shareDialog: false,
      loadingProject: false,

      showPrivacySettings: false,
      showFirstTimeModal: false,
      // Context
      timelineViewHeight: 60,
      showTimelineView: false,
      currentContextEvent: {},
      minimizeTimelineView: false,
      queryRequest: {},
      contextStartTime: null,
      contextEndTime: null,
      contextTimeWindowSeconds: 300,
      showFacetMenu: false,
      showQuestionMenu: false,
      showRightSidePanel: false,
      showSettingsDialog: false,
    }
  },
  mounted() {
    this.loadingProject = true

    this.$store.dispatch('updateProject', this.projectId)
      .then(() => {
        this.loadingProject = false
        this.checkShowDemoModal()
      })
      .catch(error => {
        console.error('[Project] Critical error:', error)
        this.loadingProject = false
      })

    EventBus.$on('showContextWindow', this.showContextWindow)
  },
  beforeDestroy() {
    EventBus.$off('showContextWindow')
  },
  computed: {
    project() {
      return this.$store.state.project
    },
    meta() {
      return this.$store.state.meta
    },
    userSettings() {
      return this.$store.state.settings
    },
    isArchived() {
      if (!this.project.status || !this.project.status.length) {
        return false
      }
      return this.project.status[0].status === 'archived'
    },
    currentUser() {
      return this.$store.state.currentUser
    },
    hasTimelines() {
      return !!(this.project.dataExports && this.project.dataExports.length)
    },
    currentRouteName() {
      return this.$route.name
    },
    systemSettings() {
      return this.$store.state.systemSettings
    },
    demoMode() {
      return this.$store.state.demoMode
    },
  },
  methods: {
    checkShowDemoModal() {
      const isRegularExploreRoute = this.$route.name === 'Explore'
      if (isRegularExploreRoute && !this.demoMode && this.$store.state.demo_visit_or_skip_count === 0 && !this.hasTimelines && !this.loadingProject) {
        this.showFirstTimeModal = true;
      }
    },
    startDemo() {
      console.log('[Project] User clicked "Try Demo"');
      this.showFirstTimeModal = false;
      this.$router.push('/demo/explore');
    },
    skipDemo() {
      console.log('[Project] User skipped demo');
      this.$store.commit('INCREMENT_DEMO_VISIT_OR_SKIP_COUNT');
      this.showFirstTimeModal = false;
    },
    deleteProject: async function () {
      if (confirm('Are you sure you want to delete all data? This cannot be undone.')) {
        try {
          await wipeAllData()
          this.$router.push({ name: 'Home' })
        } catch (e) {
          console.error('[Project] Failed to delete all data:', e)
          alert('Failed to delete data. See console for details.')
        }
      }
    },
    handleUploadData() {
      this.$router.push('/')
    },
    handleReturnHome() {
      this.$router.push('/')
    },
    startInteractiveDemo() {
      console.log('[Project] Starting interactive demo');
      this.$router.push('/demo/explore')
    },
    generateContextQuery(event) {
      let timestampMillis = this.$options.filters.formatTimestamp(event._source.primary_timestamp)
      this.contextStartTime = dayjs.utc(timestampMillis).subtract(this.contextTimeWindowSeconds, 'second')
      this.contextEndTime = dayjs.utc(timestampMillis).add(this.contextTimeWindowSeconds, 'second')
      let startChip = {
        field: '',
        value: this.contextStartTime.toISOString() + ',' + this.contextEndTime.toISOString(),
        type: 'datetime_range',
        operator: 'must',
        active: true,
      }
      let queryFilter = {
        from: 0,
        terminate_after: 40,
        size: 40,
        uploadIds: ['_all'],
        order: 'asc',
        chips: [startChip],
      }
      let queryRequest = { queryString: '*', queryFilter: queryFilter }
      return queryRequest
    },
    updateContextQuery(duration) {
      this.contextTimeWindowSeconds = duration
      this.queryRequest = this.generateContextQuery(this.currentContextEvent)
    },
    contextToSearch() {
      let queryRequest = this.generateContextQuery(this.currentContextEvent)
      queryRequest.doSearch = true
      EventBus.$emit('setQueryAndFilter', queryRequest)
      this.showTimelineView = false
    },
    showContextWindow(event) {
      this.currentContextEvent = event
      this.queryRequest = this.generateContextQuery(event)
      this.showTimelineView = true
    },
    increaseTimelineViewHeight: function () {
      this.minimizeTimelineView = false
      if (this.timelineViewHeight > 70) {
        return
      }
      this.timelineViewHeight += 30
    },
    decreaseTimelineViewHeight: function () {
      this.minimizeTimelineView = false
      if (this.timelineViewHeight < 50) {
        this.minimizeTimelineView = true
        this.timelineViewHeight = 0
        return
      }
      this.timelineViewHeight -= 30
    },
    closeTimelineView: function () {
      this.minimizeTimelineView = true
      this.timelineViewHeight = 0
    },

    toggleTheme: function () {
      this.$vuetify.theme.dark = !this.$vuetify.theme.dark
      localStorage.setItem('isDarkTheme', this.$vuetify.theme.dark.toString())
      let element = document.body
      element.dataset.theme = this.$vuetify.theme.dark ? 'dark' : 'light'
    },
    switchUI: function () {
      window.location.href = window.location.href.replace('/sketch/', '/legacy/sketch/')
    },
    toggleDrawer: function () {
      this.showLeftPanel = !this.showLeftPanel
      if (this.navigationDrawer.width > 56) {
        this.navigationDrawer.width = 56
        this.isMiniDrawer = true
      } else {
        this.navigationDrawer.width = 350
        setTimeout(() => {
          this.isMiniDrawer = false
        }, 100)
      }
    },
    updateDocumentTitle: function() {
      if (this.project && this.project.name && this.project.id) {
        document.title = `[${this.project.id}] ${this.project.name}`;
      } else {
        document.title = 'Timesketch';
      }
    },
  },
  watch: {
    sketch(newSketch) {
      if (newSketch) {
        this.updateDocumentTitle();
      }
    },
    hasTimelines(newVal, oldVal) {
      if (oldVal === 0 && newVal > 0) {
        this.showLeftPanel = true
      }
      if (oldVal > 0 && newVal === 0) {
        this.showLeftPanel = false
      }
    },
    $route(to, from) {
      this.checkShowDemoModal()
    },
  },
}
</script>

<style lang="scss">
</style>
