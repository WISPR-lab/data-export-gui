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

// modified for anonymous-research-group/data-export-gui


import Vue from 'vue'
import VueRouter from 'vue-router'
import { getLogger } from '@/utils/logger';

import Home from './views/Home.vue'
import Events from './views/Events.vue'
import Project from './views/Project.vue'
import HowToRequest from './views/HowToRequest.vue'
import DevicesMockup from './views/DevicesMockup.vue'
import DebugOPFS from './views/DebugOPFS.vue'
import { callPyodideWorker } from '@/pyodide/pyodide-client.js'
import EventBus from './event-bus.js'

import store from './store.js'
import demoDatabaseLoader from '@/demo/DemoDatabaseLoader.js'

const logger = getLogger('Router');

Vue.use(VueRouter)

const routes = [
  {
    name: 'Home',
    path: '/',
    component: Home,
  },
  {
    name: 'HowToRequest',
    path: '/how-to-request',
    component: HowToRequest,
  },
  {
    // Demo layout
    path: '/demo',
    component: Project,
    props: { projectId: 1 },
    children: [
      {
        path: 'events',
        name: 'DemoEvents',
        component: Events,
        props: { projectId: 1 },
        meta: { requiresOpfs: true, dbName: 'demo' },
      },
      {
        path: 'devices',
        name: 'DemoDevices',
        component: DevicesMockup,
        props: { projectId: 1 },
        meta: { requiresOpfs: true, dbName: 'demo' },
      },
    ],
  },
  {
    name: 'Debug',
    path: '/debug/:section',
    component: DebugOPFS,
  },
  {
    // redirect /debug to /debug/opfs
    path: '/debug',
    redirect: '/debug/opfs',
  },
  {
    // App layout (wrapper for all sketch views)
    path: '/',
    component: Project,
    props: { projectId: 1 },
    children: [
      {
        path: 'events',
        name: 'Events',
        component: Events,
        props: { projectId: 1 },
        meta: { requiresOpfs: true, dbName: 'userdata' },
      },
      {
        path: 'devices',
        name: 'Devices',
        component: DevicesMockup,
        props: { projectId: 1 },
        meta: { requiresOpfs: true, dbName: 'userdata' },
      },
    ],
  },
]

// Memoize warmup promise so it only happens once
let warmupPromise = null;

// Polls until crossOriginIsolated is true or timeoutMs elapses.
function waitForCrossOriginIsolation(timeoutMs) {
  if (window.crossOriginIsolated) return Promise.resolve(true);
  return new Promise((resolve) => {
    const start = Date.now();
    const interval = setInterval(() => {
      if (window.crossOriginIsolated) {
        clearInterval(interval);
        resolve(true);
      } else if (Date.now() - start >= timeoutMs) {
        clearInterval(interval);
        resolve(false);
      }
    }, 100);
  });
}

const router = new VueRouter({
  mode: 'hash',
  routes,
});

router.beforeEach(async (to, from, next) => {
  // Block navigation to OPFS-dependent routes if cross-origin isolation is unavailable.
  if (to.matched.some(function(r) { return r.meta && r.meta.requiresOpfs; })) {
    if (!window.crossOriginIsolated) {
      const reloadAlreadyAttempted = !!sessionStorage.getItem('coi_reload_attempted');
      if (!reloadAlreadyAttempted) {
        // Hold instead of redirecting in case a coi-serviceworker reload is soon
        EventBus.$emit('coiBootWaitingStart');
        const becameIsolated = await waitForCrossOriginIsolation(5000);
        EventBus.$emit('coiBootWaitingEnd');
        if (!becameIsolated) {
          window.opfsUnavailable = true;
          EventBus.$emit('opfsUnavailable');
          next({ path: '/', query: {} });
          return;
        }
      } else {
        window.opfsUnavailable = true;
        EventBus.$emit('opfsUnavailable');
        next({ path: '/', query: {} });
        return;
      }
    }
  }

  const targetDbName = to.meta.dbName || 'userdata'
  const isDemoRoute = targetDbName === 'demo'

  if (isDemoRoute) {
    if (!store.state.demoMode) {
      logger.debug('Entering demo mode via route:', to.path);

      const DemoController = require('@/demo/DemoController.js').default
      if (from && from.name) {
        DemoController.referrerRoute = from.path
      }

      store.commit('SET_DEMO_MODE', true)
      store.commit('SET_CURRENT_DB', 'demo')

      try {
        await demoDatabaseLoader.initializeDemoDb()
        await store.dispatch('updateProject', { projectId: 1, dbName: targetDbName })
      } catch (e) {
        logger.error('Demo initialization failed:', e)
      }
    }

    // Auto-start demo state if visiting demo events
    if (to.name === 'DemoEvents') {
      store.commit('SET_DEMO_IN_PROGRESS', true)
      store.commit('SET_DEMO_STEP', 1)
    }
  } else {
    if (store.state.demoMode) {
      logger.debug('Leaving demo mode via route:', to.path);
      store.commit('SET_DEMO_MODE', false)
      store.commit('SET_CURRENT_DB', 'userdata')
      await store.dispatch('updateProject', { projectId: 1, dbName: targetDbName })
    }
  }

  if (to.name === 'Devices' || to.name === 'DemoDevices') {
    const exports = (store.state.project && store.state.project.dataExports) || [];
    if (exports.length === 0) {
      next('/');
      return;
    }
  }
  next()
})

router.afterEach((to, from) => {
  // Warmup Pyodide when user navigates to /events
  if (to.path.includes('events')) {
    if (!warmupPromise) {
      warmupPromise = callPyodideWorker('warmup', {}).catch(err => {
        console.warn('[Router] Pyodide warmup error:', err);
        warmupPromise = null; // Reset on error so retry on next nav
      });
    }
  }
});

export default router;
