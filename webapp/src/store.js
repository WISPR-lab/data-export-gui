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
import  DB from '@/database/index.js'


Vue.use(Vuex)

const defaultState = () => {
  const getLocalTimezoneAbbr = () => {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZoneName: 'short'
    }).formatToParts(new Date())
    const tzPart = parts.find(part => part.type === 'timeZoneName')
    return tzPart ? tzPart.value : 'UTC'
  }

  // Load user settings from localStorage
  let userSettings = {
    showProcessingTimelineEvents: false,
    showLeftPanel: true,
    aiPoweredFeaturesMain: false,
    eventSummarization: false,
    generateQuery: false,
  }
  
  try {
    const stored = localStorage.getItem('userSettings')
    if (stored) {
      userSettings = { ...userSettings, ...JSON.parse(stored) }
    }
  } catch (e) {
    console.error('[Store] Failed to load settings from localStorage:', e)
  }

  return {
    // Core sketch data (virtual, not persisted to DB)
    sketch: {},
    
    // Field mappings and metadata (computed once on load)
    meta: {
      attributes: {},
      filter_labels: [],
      mappings: [],
    },
    
    // Event actions (categories from event_action field)
    eventActions: [],
    
    // Browser-specific settings
    localTimezoneAbbr: getLocalTimezoneAbbr(),
    settings: userSettings,
    eventActions: [],
    
    // UI state
    currentSearchNode: null, // Search history tree (legacy OpenSearch feature)
    enabledTimelines: [], // Timeline filter state
    snackbar: {
      active: false,
      color: '',
      message: '',
      timeout: -1,
    },
    
    // Upload processing state
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
    // SET_SCENARIOS(state, payload) {
    //   Vue.set(state, 'scenarios', payload.objects[0])
    // },
    // SET_SCENARIO_TEMPLATES(state, payload) {
    //   Vue.set(state, 'scenarioTemplates', payload.objects)
    // },
    SET_TIMELINE_TAGS(state, buckets) {
      Vue.set(state, 'tags', buckets)
    },
    SET_EVENT_LABELS(state, payload) {
      Vue.set(state.meta, 'filter_labels', payload)
    },
    SET_EVENT_ACTIONS(state, eventActions) {
      Vue.set(state, 'eventActions', eventActions)
    },
    SET_COUNT(state, payload) {
      Vue.set(state, 'count', payload)
    },
    // SET_SEARCH_NODE(state, payload) {
    //   Vue.set(state, 'currentSearchNode', payload)
    // },
    // SET_SIGMA_LIST(state, payload) {
    //   Vue.set(state, 'sigmaRuleList', payload['objects'])
    //   Vue.set(state, 'sigmaRuleList_count', payload['meta']['rules_count'])
    // },
    // SET_VISUALIZATION_LIST(state, payload) {
    //   Vue.set(state, 'savedVisualizations', payload)
    // },
    // SET_ACTIVE_USER(state, payload) {
    //   // Browser version: no user system, default to 'local-user'
    //   Vue.set(state, 'currentUser', 'local-user')
    // },
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
    SET_SNACKBAR(state, snackbar) {
      Vue.set(state, 'snackbar', snackbar)
    },
    RESET_STATE(state, payload) {
      // Browser version: reset to default with 'local-user'
      Object.assign(state, defaultState('local-user'))
    },
    SET_ENABLED_TIMELINES(state, payload) {
      Vue.set(state, 'enabledTimelines', payload)
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
      console.error('[Store] Upload failed:', errorObj)
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
    async updateSketch(context, sketchId) {
      // Virtualize the Project/Sketch (hardcoded - not saved to DB)
      const sketchName = localStorage.getItem('sketchName') || 'Local Takeout Workspace'
      const virtualSketch = {
        id: 1,
        name: sketchName,
        description: 'Browser-only processing',
        status: [{ status: 'ready' }],
        timelines: []
      }
      
      try {
        const uploads = await DB.getUploads()
        const sketch = { ...virtualSketch, timelines: uploads.objects || [] }
        const meta = await DB.getEventMeta()
        context.commit('SET_SKETCH', { objects: [sketch], meta })
      } catch (e) {
        console.error('[Store] updateSketch error:', e)
      }
    },
    resetState(context) {
      context.commit('RESET_STATE')
    },
    updateSearchNode(context, nodeId) {
      context.commit('SET_SEARCH_NODE', nodeId)
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
    setSnackBar(context, snackbar) {
      context.commit('SET_SNACKBAR', {
        active: true,
        color: snackbar.color,
        message: snackbar.message,
        timeout: snackbar.timeout,
      })
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
  },
})