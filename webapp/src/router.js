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

// modified for WISPR-lab/data-export-gui


import Vue from 'vue'
import VueRouter from 'vue-router'

import Home from './views/Home.vue'
import Canvas from './views/Canvas.vue'
import Sketch from './views/Sketch.vue'
import HowToRequest from './views/HowToRequest.vue'
import Devices from './views/Devices.vue'
import DebugOPFS from './views/DebugOPFS.vue'
import { callPyodideWorker } from '@/pyodide/pyodide-client.js'

import store from './store.js'
import DB from './database/index.js'
import demoDatabaseLoader from '@/demo/DemoDatabaseLoader.js'

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
    component: Sketch,
    props: { projectId: 1 },
    children: [
      {
        path: 'explore',
        name: 'DemoExplore',
        component: Canvas,
        props: { projectId: 1 },
      },
      {
        path: 'devices',
        name: 'DemoDevices',
        component: Devices,
        props: { projectId: 1 },
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
    component: Sketch,
    props: { projectId: 1 },
    children: [
      {
        path: 'explore',
        name: 'Explore',
        component: Canvas,
        props: { projectId: 1 },
      },
      {
        path: 'devices',
        name: 'Devices',
        component: Devices,
        props: { projectId: 1 },
      },
    ],
  },
]

// Memoize warmup promise so it only happens once
let warmupPromise = null;

const router = new VueRouter({
  mode: 'hash',
  routes,
});

router.beforeEach(async (to, from, next) => {
  const isDemoRoute = to.path.startsWith('/demo')
  
  if (isDemoRoute) {
    if (!store.state.demoMode || DB.getActiveDatabase() !== 'demo') {
      console.log('[Router] Entering demo mode via route:', to.path);
      
      const DemoController = require('@/demo/DemoController.js').default
      if (from && from.name) {
        DemoController.referrerRoute = from.path
      }
      
      store.commit('SET_DEMO_MODE', true)
      store.commit('SET_CURRENT_DB', 'demo')
      DB.setActiveDatabase('demo')
      
      try {
        await demoDatabaseLoader.initializeDemoDb()
        await store.dispatch('updateProject', 1)
      } catch (e) {
        console.error('[Router] Demo initialization failed:', e)
      }
    }
    
    // Auto-start demo state if visiting demo explore
    if (to.name === 'DemoExplore') {
      store.commit('SET_DEMO_IN_PROGRESS', true)
      store.commit('SET_DEMO_STEP', 1)
    }
  } else {
    if (store.state.demoMode || DB.getActiveDatabase() !== 'userdata') {
      console.log('[Router] Leaving demo mode via route:', to.path);
      store.commit('SET_DEMO_MODE', false)
      store.commit('SET_CURRENT_DB', 'userdata')
      DB.setActiveDatabase('userdata')
      await store.dispatch('updateProject', 1)
    }
  }
  next()
})

router.afterEach((to, from) => {
  // Warmup Pyodide when user navigates to /explore
  if (to.path.includes('explore')) {
    if (!warmupPromise) {
      warmupPromise = callPyodideWorker('warmup', {}).catch(err => {
        console.warn('[Router] Pyodide warmup error:', err);
        warmupPromise = null; // Reset on error so retry on next nav
      });
    }
  }
});

export default router;
