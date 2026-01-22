/*
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
*/

// NOTICE --- MODIFIED FOR WISPR-lab/data-export-gui


import Vue from 'vue'
import Vuex from 'vuex'
import BrowserDB from './database'

Vue.use(Vuex)

const defaultState = (currentUser) => {

  const getLocalTimezoneAbbr = () => {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZoneName: 'short'
    }).formatToParts(new Date())
    const tzPart = parts.find(part => part.type === 'timeZoneName')
    return tzPart ? tzPart.value : 'UTC'
  }

  return {
    sketch: {},
    meta: {
      attributes: {},
      filter_labels: [],
      mappings: {},
    },
    localTimezoneAbbr: getLocalTimezoneAbbr(),
    searchHistory: {},
    timeFilters: {},
    scenarios: [],
    hiddenScenarios: [],
    scenarioTemplates: [],
    graphPlugins: [],
    savedGraphs: [],
    tags: [],
    allCategories: [],
    // allCategories: [{data_type: "login_event", count: 42 }, { data_type: "message_sent", count: 15 }],
    count: 0,
    currentSearchNode: null,
    currentUser: currentUser,
    settings: {
      showProcessingTimelineEvents: false,
    },
    systemSettings: {
      ENABLE_V3_INVESTIGATION_VIEW: false,
      DFIQ_ENABLED: false,
      LLM_FEATURES_AVAILABLE: {},
    },
    activeContext: {
      scenario: {},
      facet: {},
      question: {},
    },
    snackbar: {
      active: false,
      color: '',
      message: '',
      timeout: -1,
    },
    contextLinkConf: {},
    sketchAnalyzerList: {},
    savedVisualizations: [],
    activeAnalyses: [],
    analyzerResults: [],
    enabledTimelines: [],
    sketchAccessDenied: false,
    uploadState: {
      isProcessing: false,
      currentFile: null,
      progress: 0,
      status: null,
      error: null,
      errorType: null,
      errors: [],
      warnings: [],
      success: false,
    },
  }
}

// Initial state
const state = defaultState()

export default new Vuex.Store({
  state,
  mutations: {
    SET_SKETCH(state, payload) {
      Vue.set(state, 'sketch', payload.objects[0])
      Vue.set(state, 'meta', payload.meta)
    },
    SET_SEARCH_HISTORY(state, payload) {
      Vue.set(state, 'searchHistory', payload.objects)
    },
    SET_SCENARIOS(state, payload) {
      Vue.set(state, 'scenarios', payload.objects[0])
    },
    SET_SCENARIO_TEMPLATES(state, payload) {
      Vue.set(state, 'scenarioTemplates', payload.objects)
    },
    SET_TIMELINE_TAGS(state, buckets) {
      Vue.set(state, 'tags', buckets)
    },
    SET_EVENT_LABELS(state, payload) {
      Vue.set(state.meta, 'filter_labels', payload)
    },
    SET_DATA_TYPES(state, payload) {
      let buckets = payload.objects[0]['field_bucket']['buckets']
      Vue.set(state, 'allCategories', buckets)
    },
    SET_CATEGORIES(state, categories) {
      Vue.set(state, 'allCategories', categories)
    },
    SET_COUNT(state, payload) {
      Vue.set(state, 'count', payload)
    },
    SET_SEARCH_NODE(state, payload) {
      Vue.set(state, 'currentSearchNode', payload)
    },
    SET_SIGMA_LIST(state, payload) {
      Vue.set(state, 'sigmaRuleList', payload['objects'])
      Vue.set(state, 'sigmaRuleList_count', payload['meta']['rules_count'])
    },
    SET_VISUALIZATION_LIST(state, payload) {
      Vue.set(state, 'savedVisualizations', payload)
    },
    SET_ACTIVE_USER(state, payload) {
      // Browser version: no user system, default to 'local-user'
      Vue.set(state, 'currentUser', 'local-user')
    },
    SET_ACTIVE_CONTEXT(state, payload) {
      localStorage.setItem(
        'sketchContext' + state.sketch.id.toString(),
        JSON.stringify({
          scenarioId: payload.scenarioId,
          facetId: payload.facetId,
          questionId: payload.questionId,
        })
      )
      Vue.set(state, 'activeContext', payload)
    },
    CLEAR_ACTIVE_CONTEXT(state) {
      let payload = {
        scenario: state.activeContext.scenario,
        facet: state.activeContext.facet,
        question: {},
      }
      Vue.set(state, 'activeContext', payload)
    },
    SET_GRAPH_PLUGINS(state, payload) {
      Vue.set(state, 'graphPlugins', payload)
    },
    SET_SAVED_GRAPHS(state, payload) {
      Vue.set(state, 'savedGraphs', payload.objects[0] || [])
    },
    SET_SNACKBAR(state, snackbar) {
      Vue.set(state, 'snackbar', snackbar)
    },
    RESET_STATE(state, payload) {
      // Browser version: reset to default with 'local-user'
      Object.assign(state, defaultState('local-user'))
    },
    SET_CONTEXT_LINKS(state, payload) {
      Vue.set(state, 'contextLinkConf', payload)
    },
    SET_ANALYZER_LIST(state, payload) {
      Vue.set(state, 'sketchAnalyzerList', payload)
    },
    SET_SAVED_VISUALIZATIONS(state, payload) {
      Vue.set(state, 'savedVisualizations', payload)
    },
    SET_ACTIVE_ANALYSES(state, payload) {
      Vue.set(state, 'activeAnalyses', payload)
    },
    ADD_ACTIVE_ANALYSES(state, payload) {
      const freshActiveAnalyses = [...state.activeAnalyses, ...payload]
      Vue.set(state, 'activeAnalyses', freshActiveAnalyses)
    },
    SET_ANALYZER_RESULTS(state, payload) {
      Vue.set(state, 'analyzerResults', payload)
    },
    SET_ENABLED_TIMELINES(state, payload) {
      Vue.set(state, 'enabledTimelines', payload)
    },
    SET_TIME_FILTERS(state, payload) {
      Vue.set(state, 'timeFilters', payload)
    },
    ADD_ENABLED_TIMELINES(state, payload) {
      const freshEnabledTimelines = [...state.enabledTimelines, ...payload]
      Vue.set(state, 'enabledTimelines', freshEnabledTimelines)
    },
    REMOVE_ENABLED_TIMELINES(state, payload) {
      Vue.set(
        state,
        'enabledTimelines',
        state.enabledTimelines.filter((tl) => !payload.includes(tl))
      )
    },
    TOGGLE_ENABLED_TIMELINE(state, payload) {
      if (state.enabledTimelines.includes(payload)) {
        Vue.set(
          state,
          'enabledTimelines',
          state.enabledTimelines.filter((tl) => payload !== tl)
        )
      } else {
        const freshEnabledTimelines = [...state.enabledTimelines, payload]
        Vue.set(state, 'enabledTimelines', freshEnabledTimelines)
      }
    },
    SET_SYSTEM_SETTINGS(state, payload) {
      Vue.set(state, 'systemSettings', payload || {})
    },
    SET_USER_SETTINGS(state, payload) {
      Vue.set(state, 'settings', payload.objects[0] || {})
    },
    SET_SKETCH_ACCESS_DENIED(state, payload) {
      Vue.set(state, 'sketchAccessDenied', payload)
    },

       // Upload processing
    SET_UPLOAD_STATE(state, payload) {
      Vue.set(state, 'uploadState', { ...state.uploadState, ...payload })
    },
    START_UPLOAD(state, fileName) {
      Vue.set(state, 'uploadState', {
        isProcessing: true,
        currentFile: fileName,
        progress: 0,
        status: 'validating',
        error: null,
      })
    },
    UPDATE_UPLOAD_PROGRESS(state, { status, progress, error }) {
      Vue.set(state, 'uploadState', {
        ...state.uploadState,
        status,
        progress,
        error: error || null,
      })
    },
    COMPLETE_UPLOAD(state, payload = {}) {
      // Accept optional summary object with warnings
      Vue.set(state, 'uploadState', {
        isProcessing: false,
        currentFile: null,
        progress: 100,
        status: 'complete',
        error: null,
        errorType: null,
        errors: [],
        warnings: payload.warnings || [],
        success: true,
      })

    },
    FAIL_UPLOAD(state, payload) {
      // Accept summary object with errorType, errors, warnings
      const errorObj = typeof payload === 'string' ? { errors: [payload] } : payload;
      Vue.set(state, 'uploadState', {
        ...state.uploadState,
        isProcessing: false,
        status: 'error',
        error: (errorObj.errors && errorObj.errors[0]) || errorObj.error || 'Upload failed',
        errorType: errorObj.errorType || null,
        errors: errorObj.errors || [],
        warnings: errorObj.warnings || [],
        success: false,
      })
    },
  },
  actions: {
    updateSketch(context, sketchId) {
      context.commit('SET_SKETCH_ACCESS_DENIED', false)
      return BrowserDB.getSketch(sketchId)
        .then((response) => {
          context.commit('SET_SKETCH', response.data)
          context.commit('SET_ACTIVE_USER', response.data)
          context.dispatch('updateTimelineTags', { sketchId: sketchId })
          context.dispatch('updateDataTypes', sketchId)
          context.dispatch('updateCategories', sketchId)
        })
        .catch((e) => {
          console.error(e)
          context.commit('SET_SKETCH_ACCESS_DENIED', true)
        })
    },
    updateCount(context, sketchId) {
      // Count events for all timelines in the sketch
      return BrowserDB.countSketchEvents(sketchId)
        .then((response) => {
          context.commit('SET_COUNT', response.data.meta.count)
        })
        .catch((e) => { console.error(e) })
    },
    resetState(context) {
      context.commit('RESET_STATE')
    },
    updateSearchNode(context, nodeId) {
      context.commit('SET_SEARCH_NODE', nodeId)
    },
    updateSearchHistory(context, sketchId) {
      // Browser version: stub (no server API available)
      return Promise.resolve()
    },
    updateTimeFilters(context, sketchId) {
      // Browser version: stub (no server API available)
      return Promise.resolve()
    },
    updateScenarios(context, sketchId) {
      // Browser version: stub (DFIQ scenarios not implemented)
      return Promise.resolve()
    },
    updateScenarioTemplates(context, sketchId) {
      // Browser version: stub (DFIQ scenarios not implemented)
      return Promise.resolve()
    },
    updateEventLabels(context, { label: inputLabel, num }) {
      if (!inputLabel || !num) {
        return
      }
      let allLabels = context.state.meta.filter_labels
      let label = allLabels.find(label => label.label === inputLabel);
      if (label !== undefined) {
        label.count += num
      } else {
        allLabels.push({ label: inputLabel, count: num })
      }
      context.commit('SET_EVENT_LABELS', allLabels)
    },
    updateTimelineTags(context, payload) {
      // Browser version: tags aggregation not implemented yet
      // TODO: Compute from BrowserDB.search() results
      return Promise.resolve()
    },
    updateDataTypes(context, sketchId) {
      // Browser version: data type aggregation not implemented yet
      // TODO: Compute from BrowserDB.search() results
      return Promise.resolve()
    },
    updateCategories(context, sketchId) {
      return BrowserDB.getEvents(sketchId)
        .then((events) => {
          if (!events || events.length === 0) {
            context.commit('SET_CATEGORIES', [])
            return
          }
          const categoryMap = {}
          events.forEach((event) => {
            const category = event.category || 'uncategorized'
            if (categoryMap[category]) {
              categoryMap[category].count += 1
            } else {
              categoryMap[category] = { category, count: 1 }
            }
          })
          const categories = Object.values(categoryMap).sort((a, b) => b.count - a.count)
          context.commit('SET_CATEGORIES', categories)
        })
        .catch((e) => {
          console.error('Error computing categories:', e)
          context.commit('SET_CATEGORIES', [])
        })
    },
    updateSigmaList(context) {
      console.warn('store.js::updateSigmaList: this is just a stub')
      return Promise.resolve()
      // ApiClient.getSigmaRuleList()
      //   .then((response) => {
      //     context.commit('SET_SIGMA_LIST', response.data)
      //   })
      //   .catch((e) => { console.error(e) })
    },
    updateSavedVisualizationList(context, sketchId) {
      console.warn('store.js::updateSavedVisualizationList: this is just a stub')
      return Promise.resolve()
      // ApiClient.getAggregations(sketchId)
      //   .then((response) => {
      //     context.commit('SET_VISUALIZATION_LIST', response.data.objects[0] || [])
      //   })
      //   .catch((e) => { console.error(e) })
    },
    setActiveContext(context, activeScenarioContext) {
      context.commit('SET_ACTIVE_CONTEXT', activeScenarioContext)
    },
    clearActiveContext(context) {
      context.commit('CLEAR_ACTIVE_CONTEXT')
    },
    setSnackBar(context, snackbar) {
      context.commit('SET_SNACKBAR', {
        active: true,
        color: snackbar.color,
        message: snackbar.message,
        timeout: snackbar.timeout,
      })
    },
    updateContextLinks(context) {
      console.warn('store.js::updateContextLinks: this is just a stub')
      return Promise.resolve()
      // ApiClient.getContextLinkConfig()
      //   .then((response) => {
      //     context.commit('SET_CONTEXT_LINKS', response.data)
      //   })
      //   .catch((e) => { console.error(e) })
    },
    updateGraphPlugins(context) {
      console.warn('store.js::updateGraphPlugins: this is just a stub')
      return Promise.resolve()
      // ApiClient.getGraphPluginList()
      //   .then((response) => {
      //     context.commit('SET_GRAPH_PLUGINS', response.data)
      //   })
      //   .catch((e) => { console.error(e) })
    },
    updateSavedGraphs(context, sketchId) {
      console.warn('store.js::updateSavedGraphs: this is just a stub')
      return Promise.resolve()
      // if (!sketchId) {
      //   sketchId = context.state.sketch.id
      // }
      // ApiClient.getSavedGraphList(sketchId)
      //   .then((response) => {
      //     context.commit('SET_SAVED_GRAPHS', response.data)
      //   })
      //   .catch((e) => {
      //     console.error(e)
      //   })
    },
    updateAnalyzerList(context, sketchId) {
      console.warn('store.js::updateAnalyzerList: this is just a stub')
      return Promise.resolve()
      // if (!sketchId) {
      //   sketchId = context.state.sketch.id
      // }
      // ApiClient.getAnalyzers(sketchId)
      //   .then((response) => {
      //     let analyzerList = {}
      //     if (response.data !== undefined) {
      //       response.data.forEach((analyzer) => {
      //         analyzerList[analyzer.name] = analyzer
      //       })
      //     }
      //     context.commit('SET_ANALYZER_LIST', analyzerList)
      //   })
      //   .catch((e) => {
      //     console.error(e)
      //   })
    },
    updateActiveAnalyses(context, activeAnalyses) {
      context.commit('SET_ACTIVE_ANALYSES', activeAnalyses)
    },
    addActiveAnalyses(context, activeAnalyses) {
      context.commit('ADD_ACTIVE_ANALYSES', activeAnalyses)
    },
    updateAnalyzerResults(context, analyzerResults) {
      context.commit('SET_ANALYZER_RESULTS', analyzerResults)
    },
    enableTimeline(context, timeline) {
      context.commit('ADD_ENABLED_TIMELINES', [timeline])
    },
    disableTimeline(context, timeline) {
      context.commit('REMOVE_ENABLED_TIMELINES', [timeline])
    },
    updateEnabledTimelines(context, enabledTimelines) {
      context.commit('SET_ENABLED_TIMELINES', enabledTimelines)
    },
    toggleEnabledTimeline(context, timelineId) {
      context.commit('TOGGLE_ENABLED_TIMELINE', timelineId)
    },
    updateSystemSettings(context) {
      console.warn('store.js::updateSystemSettings: this is just a stub')
      return Promise.resolve()
      // return ApiClient.getSystemSettings()
      //   .then((response) => {
      //     context.commit('SET_SYSTEM_SETTINGS', response.data)
      //   })
      //   .catch((e) => {
      //     console.error(e)
      //   })
    },
    updateUserSettings(context) {
      console.warn('store.js::updateUserSettings: this is just a stub')
      return Promise.resolve()
      // return ApiClient.getUserSettings()
      //   .then((response) => {
      //     context.commit('SET_USER_SETTINGS', response.data)
      //   })
      //   .catch((e) => {
      //     console.error(e)
      //   })
    },
  },
})