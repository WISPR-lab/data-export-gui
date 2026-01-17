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
import VueRouter from 'vue-router'

import Home from './views/Home.vue'
import Canvas from './views/Canvas.vue'
import Sketch from './views/Sketch.vue'
import HowToRequest from './views/HowToRequest.vue'

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
    // App layout (wrapper for all sketch views)
    path: '/',
    component: Sketch,
    props: { sketchId: 1 },
    children: [
      {
        path: 'explore',
        name: 'Explore',
        component: Canvas,
        props: { sketchId: 1 },
      },
      {
        path: 'intelligence',
        name: 'Intelligence',
        component: Canvas,
        props: { sketchId: 1 },
      },
      {
        path: 'sigma',
        component: Canvas,
        props: { sketchId: 1 },
        children: [
          {
            path: 'new',
            name: 'SigmaNewRule',
            component: Canvas,
            props: { sketchId: 1 },
          },
          {
            path: 'edit/:ruleId',
            name: 'SigmaEditRule',
            component: Canvas,
            props: { sketchId: 1, ruleId: true },
          },
        ]
      },
      {
        path: 'visualization',
        component: Canvas,
        props: { sketchId: 1 },
        children: [
          {
            path: 'new',
            name: 'VisualizationNew',
            component: Canvas,
            props: { sketchId: 1 },
          },
          {
            path: 'view/:aggregationId',
            name: 'VisualizationView',
            component: Canvas,
            props: { sketchId: 1, aggregationId: true },
          },
        ]
      },
      {
        path: 'graph',
        name: 'Graph',
        component: Canvas,
        props: { sketchId: 1 },
      },
      {
        path: 'story/:storyId',
        name: 'Story',
        component: Canvas,
        props: { sketchId: 1, storyId: true },
      },
      {
        path: 'analyzers',
        name: 'Analyze',
        component: Canvas,
        props: { sketchId: 1 },
      },
    ],
  },
]

export default new VueRouter({
  mode: 'history',
  routes,
})
