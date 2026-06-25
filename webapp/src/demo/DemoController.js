import router from '@/router.js'
import EventBus from '@/event-bus.js'
import { getStepDefinitions } from './DemoStepDefns.js'

const DEMO_DEBUGGING = false

class DemoController {
  constructor() {
    this.currentStepId = null
    this.store = null
    this._actionListener = null
    this._lastUiUpdate = null
    this.referrerRoute = null
  }

  getStepDefinitions() {
    return getStepDefinitions()
  }

  async basicInitialize(store) {
    this._setAllExportsVisible(store)
    this._clearSearch()
    this._forceCollapseAllRows()
    this._closeAllMenus()
  }

  forceOpenTutorials() {
    if (this._tutorialsInterval) {
        clearInterval(this._tutorialsInterval)
        this._tutorialsInterval = null
    }
    this._tutorialsInterval = setInterval(() => {
        const menuVisible = document.querySelector('.interactive-demo-link')
        if (!menuVisible) {
            const btn = document.querySelector('#tsTutorialsButton')
            if (btn) {
                btn.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }))
            }
        }
    }, 50)
  }
  
    stopForceOpenTutorials() {
    if (this._tutorialsInterval) {
        clearInterval(this._tutorialsInterval)
        this._tutorialsInterval = null
    }
    
    // Dispatch mouseleave on the activator button
    const btn = document.querySelector('#tsTutorialsButton')
    if (btn) {
        btn.dispatchEvent(new MouseEvent('mouseleave', { bubbles: true }))
    }
    
    // Dispatch mouseleave on active menus to trigger Vuetify close handlers
    const activeMenus = document.querySelectorAll('.v-menu__content, .menuable__content__active')
    activeMenus.forEach(menu => {
        menu.dispatchEvent(new MouseEvent('mouseleave', { bubbles: true }))
    })
    
    this._closeAllMenus()
  }

  start(store) {
    if (this.store) {
        if (!this.currentStepId) this.runStep('WELCOME')
        return
    }

    if (DEMO_DEBUGGING) console.log('[DemoController] Initializing start sequence...');
    this.store = store
    this.store.commit('INCREMENT_DEMO_VISIT_OR_SKIP_COUNT')

    this.onStart(this.store)

    this._setupActionListeners()

    // auto-cleanup if demoMode is turned off in store (e.g. via router navigation)
    this._storeUnsubscribe = this.store.subscribe((mutation) => {
      if (mutation.type === 'SET_DEMO_MODE' && mutation.payload === false) {
        if (DEMO_DEBUGGING) console.log('[DemoController] demoMode disabled in store, completing demo');
        this.complete()
      }
    })

    this.runStep('WELCOME')
  }

  onStart(store) {
      this._setAllExportsVisible(store)
      // run async cleanup in background to prevent blocking the boot sequence
      this._clearAllTags(store).catch(e => console.error('[DemoController] Failed to clear tags on start:', e))
  }


  _setupActionListeners() {
    if (this._actionListener) {
      EventBus.$off('demo:action', this._actionListener)
    }
    
    this._actionListener = (actionType) => {
      const allSteps = this.getStepDefinitions()
      const currentStepDef = allSteps.find(s => s.id === this.currentStepId)
      if (!currentStepDef) return

      if (DEMO_DEBUGGING) console.log(`[DemoController] Action received: ${actionType} (current step: ${this.currentStepId})`);

      if (actionType === 'next-click' || actionType === 'prev-click') {
          if (actionType === 'next-click') this.moveNext()
          else this.movePrevious()
          return
      }

      if (actionType === currentStepDef.action) {
          this.moveNext()
      } else if (actionType === 'complete') {
          this.complete()
      }
    }
    
    EventBus.$on('demo:action', this._actionListener)
  }

  moveNext() {
    const allSteps = this.getStepDefinitions()
    const currentIndex = allSteps.findIndex(s => s.id === this.currentStepId)
    const nextStep = allSteps[currentIndex + 1]
    
    if (!nextStep) {
      this.complete()
      return
    }
    this.runStep(nextStep.id)
  }

  movePrevious() {
    const allSteps = this.getStepDefinitions()
    const currentIndex = allSteps.findIndex(s => s.id === this.currentStepId)
    const prevStep = allSteps[currentIndex - 1]
    
    if (!prevStep) return
    this.runStep(prevStep.id)
  }


  async runStep(stepId) {
    const allSteps = this.getStepDefinitions()
    let isForward = true

    if (this.currentStepId) {
        const currentIndex = allSteps.findIndex(s => s.id === this.currentStepId)
        const nextIndex = allSteps.findIndex(s => s.id === stepId)
        isForward = nextIndex > currentIndex

        const currentDef = allSteps.find(s => s.id === this.currentStepId)
        if (currentDef && currentDef.onLeave && this.store) {
            if (DEMO_DEBUGGING) console.log(`[DemoController] Executing onLeave for ${this.currentStepId} (isForward: ${isForward})`);
            await currentDef.onLeave(this, this.store, isForward)
        }
    }

    const stepIndex = allSteps.findIndex(s => s.id === stepId)
    const stepDef = allSteps[stepIndex]
    if (!stepDef) return

    this.currentStepId = stepId
    const stepNumber = stepIndex + 1

    if (this.store) {
      this.store.commit('SET_DEMO_STEP', stepNumber)
      this.store.commit('SET_DEMO_IN_PROGRESS', true)
      
      if (stepDef.onEnter) {
          if (DEMO_DEBUGGING) console.log(`[DemoController] Executing onEnter for ${stepId} (isForward: ${isForward})`);
          await stepDef.onEnter(this, this.store, isForward)
      }
    }

    // visual overlay updates
    this._lastUiUpdate = {
      id: stepDef.id,
      title: stepDef.title,
      content: stepDef.content,
      visibleElements: stepDef.visibleElements === 'body' ? undefined : stepDef.visibleElements,
      clickableElement: stepDef.clickableElement,
      blockedElements: stepDef.blockedElements,
      arrowPosition: stepDef.arrowPosition,
      finishButtonText: stepDef.finishButtonText,
      isFirst: stepIndex === 0,
      isLast: stepIndex === allSteps.length - 1,
      stepNumber: stepNumber,
      totalSteps: allSteps.length
    }

    EventBus.$emit('demo:update-ui', this._lastUiUpdate)
    if (DEMO_DEBUGGING) console.log('[DemoController] First step broadcasted.');
  }

  getCurrentUiState() {
      return this._lastUiUpdate
  }

  complete() {
    this.stopForceOpenTutorials()
    const isFinal = this.currentStepId === 'FINISH'
    if (DEMO_DEBUGGING) console.log('[DemoController] Demo complete/exited');
    this._lastUiUpdate = null
    EventBus.$emit('demo:update-ui', null) // close overlay
    
    if (this.store) {
      this.store.commit('SET_DEMO_IN_PROGRESS', false)
      this.store.commit('SET_DEMO_STEP', 0)
      if (isFinal) {
        this.store.commit('INCREMENT_DEMO_FINISHED_COUNT')
      }
    }

    if (this._storeUnsubscribe) {
        this._storeUnsubscribe()
        this._storeUnsubscribe = null
    }

    if (this._actionListener) {
      EventBus.$off('demo:action', this._actionListener)
      this._actionListener = null
    }

    this.store = null
    this.currentStepId = null

    const targetRoute = this.referrerRoute || { name: 'Home' }
    this.referrerRoute = null
    router.push(targetRoute)
  }

  // --- Helper Methods ---

  _setFirstTimelineVisible(store, isVisible) {
    const firstTl = store.state.project.dataExports[0]
    if (!firstTl) return
    
    const isCurrentlyVisible = store.state.enabledDataExports.includes(firstTl.id)
    if (isVisible && !isCurrentlyVisible) {
      store.commit('ADD_ENABLED_DATA_EXPORTS', [firstTl.id])
    } else if (!isVisible && isCurrentlyVisible) {
      store.commit('REMOVE_ENABLED_DATA_EXPORTS', [firstTl.id])
    }
  }

  _setAllExportsVisible(store) {
    const allTlIds = store.state.project.dataExports.map(t => t.id)
    if (allTlIds.length > 0) {
      store.commit('SET_ENABLED_DATA_EXPORTS', allTlIds)
    }
  }

  _forceExpandFirstRow() {
      EventBus.$emit('demo:force-expand-first-row')
  }

  _forceCollapseAllRows() {
      EventBus.$emit('demo:force-collapse-all')
  }

  _closeAllMenus() {
      // send an Escape key event to close Vuetify menus/dialogs
      const escapeEvent = new KeyboardEvent('keydown', {
          key: 'Escape',
          code: 'Escape',
          keyCode: 27,
          which: 27,
          bubbles: true,
          cancelable: true
      });
      document.dispatchEvent(escapeEvent);
      // Fallback: click a neutral area
      document.body.click();
  }

  _clearSearch() {
      if (DEMO_DEBUGGING) console.log('[DemoController] Magically clearing search filters');
      EventBus.$emit('setQueryAndFilter', { 
          queryFilter: { 
              chips: [], 
              order: 'asc', 
              size: 40, 
              terminate_after: 40, 
              from: 0 
          } 
      })
  }

  async _clearAllTags(store) {
      if (DEMO_DEBUGGING) console.log('[DemoController] Wiping all tags for fresh demo');
      const DB = require('@/database/index.js').default
      await DB.clearAllTags()
      if (store) {
          store.commit('SET_TIMELINE_TAGS', [])
          store.commit('SET_EVENT_LABELS', [])
      }
  }

  _forceOpenTagMenu() {
      setTimeout(() => {
          const tagMenuContent = document.querySelector('.menuable__content__active .v-chip') || 
                               document.querySelector('.menuable__content__active .v-list')
          
          if (!tagMenuContent) {
              if (DEMO_DEBUGGING) console.log('[DemoController] Forcing tag menu open');
              this._secureClick('#tsEventTable tbody tr:first-child .v-icon[title*="Modify tags"]')
          }
      }, 100)
  }

   async _addSampleTag(store) {
       if (DEMO_DEBUGGING) console.log('[DemoController] Programmatically adding sample tag');
       const DB = require('@/database/index.js').default
       const result = await DB.searchEvents('', { size: 1, order: 'asc' })
       if (result.objects && result.objects.length > 0) {
           const targetEvent = result.objects[0]
           await DB.updateEventTags(targetEvent._id, ['bad'])
           
           if (store) {
               store.dispatch('updateEventLabels', { label: 'bad', num: 1 })
           }
           
           setTimeout(() => {
               EventBus.$emit('setQueryAndFilter', { doSearch: true })
           }, 50)
       }
   }

  _forceApplySampleFilter() {
      if (DEMO_DEBUGGING) console.log('[DemoController] Forcing sample filter for result step');
      EventBus.$emit('setQueryAndFilter', { 
          doSearch: true,
          chip: {
            field: 'event_action',
            value: 'access',
            type: 'term',
            operator: 'must',
            active: true,
          }
      })
  }

  _secureClick(selector) {
      const el = document.querySelector(selector)
      if (el) {
          const clickEvent = new MouseEvent('click', {
              view: window,
              bubbles: false,
              cancelable: true
          });
          el.dispatchEvent(clickEvent);
      }
  }
}

export default new DemoController()