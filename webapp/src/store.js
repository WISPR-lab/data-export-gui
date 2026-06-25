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
// modified for WISPR-lab/data-export-gui


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

  let userSettings = {
    showProcessingData: false,
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
    localStorage.removeItem('demoWasOffered')
  } catch (e) {
    console.error('[Store] Failed to load settings or clean legacy state:', e)
  }

  return {
    project: {},
    meta: {
      attributes: {},
      filter_labels: [],
      mappings: [],
    },
    eventActions: [],
    tags: [],
    localTimezoneAbbr: getLocalTimezoneAbbr(),
    settings: userSettings,
    currentSearchNode: null,
    enabledDataExports: [],
    snackbar: {
      active: false,
      color: '',
      message: '',
      timeout: -1,
    },
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
    demoMode: false,
    currentDb: 'userdata',
    demoInProgress: false,
    demoStep: 0,
    demo_visit_or_skip_count: 0,
    demoFinishCount: 0,
  }
}

const state = defaultState()

export default new Vuex.Store({
  state,
  mutations: {
    SET_PROJECT(state, payload) {
      Vue.set(state, 'project', payload.objects[0])
      Vue.set(state, 'meta', payload.meta)
    },

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

    SET_SNACKBAR(state, snackbar) {
      Vue.set(state, 'snackbar', snackbar)
    },
    RESET_STATE(state, payload) {
      Object.assign(state, defaultState('local-user'))
    },
    SET_ENABLED_DATA_EXPORTS(state, payload) {
      Vue.set(state, 'enabledDataExports', payload)
    },

    TOGGLE_ENABLED_DATA_EXPORT(state, payload) {
      if (state.enabledDataExports.includes(payload)) {
        Vue.set(
          state,
          'enabledDataExports',
          state.enabledDataExports.filter((de) => payload !== de)
        )
      } else {
        const freshEnabledDataExports = [...state.enabledDataExports, payload]
        Vue.set(state, 'enabledDataExports', freshEnabledDataExports)
      }
    },

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
    SET_DEMO_MODE(state, demoMode) {
      Vue.set(state, 'demoMode', demoMode)
    },
    SET_CURRENT_DB(state, dbName) {
      Vue.set(state, 'currentDb', dbName)
    },
    SET_DEMO_IN_PROGRESS(state, value) {
      Vue.set(state, 'demoInProgress', value)
    },
    SET_DEMO_STEP(state, step) {
      Vue.set(state, 'demoStep', step)
    },
    INCREMENT_DEMO_VISIT_OR_SKIP_COUNT(state) {
      Vue.set(state, 'demo_visit_or_skip_count', state.demo_visit_or_skip_count + 1)
    },
    INCREMENT_DEMO_FINISH_COUNT(state) {
      Vue.set(state, 'demoFinishCount', state.demoFinishCount + 1)
    },
  },
  actions: {
    async updateProject(context, projectId) {
      if (!window.crossOriginIsolated) {
        console.warn('[Store.updateProject] security headers missing. skippng db init.');
        return;
      }

      let projectName = localStorage.getItem('projectName') || 'My Data'
      if (context.state.demoMode) {
        projectName = 'Instagram Demo Data'
      }
      
      const virtualProject = {
        id: context.state.demoMode ? 2 : 1,
        name: projectName,
        description: 'Browser-only processing',
        status: [{ status: 'ready' }],
        dataExports: []
      }
      
      try {
        console.log('[Store.updateProject] Fetching uploads from database...');
        const uploads = await DB.getUploads()
        console.log('[Store.updateProject] Received uploads:', uploads.uploads);
        const project = { ...virtualProject, dataExports: uploads.uploads || [] }
        const meta = await DB.getEventMeta()
        console.log('[Store.updateProject] Committing SET_PROJECT with dataExports:', project.dataExports.map(t => ({ id: t.id, name: t.name, color: t.color })));
        context.commit('SET_PROJECT', { objects: [project], meta })
      } catch (e) {
        console.error('[Store] updateProject error:', e)
      }
    },
    resetState(context) {
      context.commit('RESET_STATE')
    },

    updateEventLabels(context, { label: inputLabel, num }) {
      if (!inputLabel || !num) {
        return
      }
      let allLabels = context.state.meta.filter_labels
      let label = allLabels.find(label => label.tag === inputLabel);
      if (label !== undefined) {
        label.count += num
      } else {
        allLabels.push({ tag: inputLabel, count: num })
      }
      allLabels = allLabels.filter(label => label.count > 0)
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

    updateEnabledDataExports(context, enabledDataExports) {
      context.commit('SET_ENABLED_DATA_EXPORTS', enabledDataExports)
    },
    toggleEnabledDataExport(context, dataExportId) {
      context.commit('TOGGLE_ENABLED_DATA_EXPORT', dataExportId)
    },
    setDemoMode(context, demoMode) {
      context.commit('SET_DEMO_MODE', demoMode)
    },
    setCurrentDb(context, dbName) {
      context.commit('SET_CURRENT_DB', dbName)
    },
    setDemoInProgress(context, value) {
      context.commit('SET_DEMO_IN_PROGRESS', value)
    },
    setDemoStep(context, step) {
      context.commit('SET_DEMO_STEP', step)
    },
    clearDemoState(context) {
      // Clear UI state when switching out of demo mode to prevent filter leakage
      context.commit('SET_EVENT_LABELS', [])
      context.commit('SET_ENABLED_DATA_EXPORTS', [])
      // Reset demo progress
      context.commit('SET_DEMO_IN_PROGRESS', false)
      context.commit('SET_DEMO_STEP', 0)
    },
  },
})