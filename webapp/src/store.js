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
import Vue from 'vue'
import Vuex from 'vuex'


Vue.use(Vuex)

const defaultState = (currentUser) => {
  return {
    // Core sketch state
    sketch: {},
    meta: {},
    timelines: [],
    tags: [],
    enabledTimelines: [],
    
    // Upload processing state
    uploadState: {
      isProcessing: false,
      currentFile: null,
      progress: 0,
      status: '', // 'validating', 'parsing', 'inserting', 'complete', 'error'
      error: null,
    },
    
    // UI state
    currentUser: currentUser,
    settings: {
      showProcessingTimelineEvents: false,
    },
    systemSettings: {
      ENABLE_V3_INVESTIGATION_VIEW: false,
      DFIQ_ENABLED: false,
      LLM_FEATURES_AVAILABLE: {},
    },
    snackbar: {
      active: false,
      color: '',
      message: '',
      timeout: -1,
    },
    timeFilters: {},
    enabledTimelines: [],
  }
}

// Initial state
const state = defaultState()

export default new Vuex.Store({
  state,
  mutations: {
    // Core sketch state
    SET_SKETCH(state, payload) {
      Vue.set(state, 'sketch', payload.objects[0] || {})
      Vue.set(state, 'meta', payload.meta || {})
    },
    SET_TIMELINES(state, payload) {
      Vue.set(state, 'timelines', payload.objects || [])
    },
    SET_TAGS(state, buckets) {
      Vue.set(state, 'tags', buckets)
    },
    
    // Timeline visibility
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
    COMPLETE_UPLOAD(state) {
      Vue.set(state, 'uploadState', {
        isProcessing: false,
        currentFile: null,
        progress: 100,
        status: 'complete',
        error: null,
      })
    },
    FAIL_UPLOAD(state, error) {
      Vue.set(state, 'uploadState', {
        ...state.uploadState,
        isProcessing: false,
        status: 'error',
        error,
      })
    },
    
    // UI
    SET_SNACKBAR(state, snackbar) {
      Vue.set(state, 'snackbar', snackbar)
    },
    SET_SETTINGS(state, payload) {
      Vue.set(state, 'settings', payload || {})
    },
    SET_SYSTEM_SETTINGS(state, payload) {
      Vue.set(state, 'systemSettings', payload || {})
    },
    SET_TIME_FILTERS(state, payload) {
      Vue.set(state, 'timeFilters', payload)
    },
    RESET_STATE(state, payload) {
      Object.assign(state, defaultState('localuser'))
    },
  },
  actions: {
    resetState(context) {
      context.commit('RESET_STATE')
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
