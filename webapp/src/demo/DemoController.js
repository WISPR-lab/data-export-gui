import router from '@/router.js'
import EventBus from '@/event-bus.js'

class DemoController {
  constructor() {
    this.currentStepId = null
    this.store = null
    this._actionListener = null
    this._lastUiUpdate = null
  }

  getStepDefinitions() {
    return [
      {
        id: 'WELCOME',
        view: 'explore',
        visibleElements: 'body',
        title: 'Welcome',
        content: 'This demo will walk you through the core features of LEStrADE using sample Instagram activity. \n\n (Tip: You can use the ← and → keys to navigate)',
        action: 'next-click',
        onEnter: (store) => {
            this._setAllTimelinesVisible(store)
            this._forceCollapseAllRows()
            this._closeAllMenus()
            this._clearSearch()
            this._clearAllTags(store).catch(e => console.error(e))
        },
        onLeave: (store) => {
            this._setAllTimelinesVisible(store)
            this._forceCollapseAllRows()
            this._closeAllMenus()
            this._clearSearch()
        }
      },
      {
        id: 'OPEN_TIMELINE_MENU',
        view: 'explore',
        visibleElements: '.timeline-chip:first-child',
        clickableElement: '#tsTimelineChipMenu',
        title: 'Timeline Visibility',
        content: 'Each chip represents a different data export you\'ve uploaded. Let\'s start by opening the menu.',
        action: 'timeline-menu-opened',
        onEnter: (store) => {
            this._setAllTimelinesVisible(store)
            this._forceCollapseAllRows()
            this._closeAllMenus()
            this._clearSearch()
        },
        onLeave: (store) => {
            this._setAllTimelinesVisible(store)
            this._forceCollapseAllRows()
        }
      },
      {
        id: 'HIDE_TIMELINE_DATA',
        view: 'explore',
        visibleElements: ['.timeline-chip:first-child', '.menuable__content__active'],
        clickableElement: '#tsTimelineVisibilityToggle',
        title: 'Data Export Visibility',
        content: 'You can temporarily hide this export to focus on other data. Try toggling it off and on.',
        action: 'timeline-toggled',
        onEnter: (store) => {
            this._setAllTimelinesVisible(store)
            this._forceCollapseAllRows()
            this._setFirstTimelineVisible(store, true)
            // Ensure menu is open if they skipped to here
            const menuVisible = document.querySelector('.menuable__content__active')
            if (!menuVisible) {
                this._secureClick('#tsTimelineChipMenu')
            }
        },
        onLeave: (store) => {
            this._setFirstTimelineVisible(store, false)
            this._closeAllMenus()
        }
      },
      {
        id: 'SHOW_TIMELINE_DATA',
        view: 'explore',
        visibleElements: '.timeline-chip:first-child',
        clickableElement: '.timeline-chip:first-child',
        blockedElements: ['#tsTimelineChipMenu'], // Prevent menu opening
        title: 'Data Export Visibility',
        content: 'You can bring it back anytime by clicking on the chip itself. Try re-enabling it now.',
        action: 'timeline-toggled',
        onEnter: (store) => {
            this._forceCollapseAllRows()
            this._closeAllMenus()
            this._setFirstTimelineVisible(store, false)
        },
        onLeave: (store) => {
            this._setFirstTimelineVisible(store, true)
        }
      },
      {
        id: 'SHOW_TIMELINE_DATA2',
        view: 'explore',
        visibleElements: '.timeline-chip:first-child',
        clickableElement: '',
        blockedElements: ['#tsTimelineChipMenu', '.timeline-chip:first-child'],
        title: 'Data Export Visibility',
        content: 'Done! Let\'s move on to exploring your data.',
        action: 'timeline-toggled',
        onEnter: (store) => {
            this._forceCollapseAllRows()
            this._closeAllMenus()
            this._setFirstTimelineVisible(store, true)
        },
        onLeave: (store) => {
            this._setFirstTimelineVisible(store, true)
            this._clearSearch()
        }
      },
      {
        id: 'EVENTS_MACRO',
        view: 'explore',
        visibleElements: '#tsEventTable',
        title: 'The Events Table',
        content: 'This table shows every action extracted from your data exports, sorted chronologically. This is the heart of your investigation.',
        action: 'next-click',
        onEnter: (store) => {
            this._setFirstTimelineVisible(store, true)
            this._clearSearch()
            this._forceCollapseAllRows()
            this._closeAllMenus()
        },
        onLeave: (store) => {
            this._setFirstTimelineVisible(store, true)
            this._clearSearch()
        }
      },
      {
        id: 'EXPAND_EVENT',
        view: 'explore',
        visibleElements: '#tsEventTable tbody tr:first-child',
        clickableElement: '#tsEventTable tbody tr:first-child',
        title: 'Deep Dive',
        content: 'Click on the first event to expand it and see the raw details and metadata extracted by LEStrADE.',
        action: 'event-expanded',
        onEnter: (store) => {
            this._setFirstTimelineVisible(store, true)
            this._clearSearch()
            this._forceCollapseAllRows()
            this._closeAllMenus()
        },
        onLeave: (store) => {
            // force expand if user clicked Next
            this._forceExpandFirstRow()
        }
      },
      {
        id: 'READ_EVENT_DETAILS',
        view: 'explore',
        visibleElements: ['#tsEventTable tbody tr:first-child', '#tsEventTable tr.v-data-table__expanded__content'],
        title: 'Deep Dive',
        content: 'Take a moment to review the metadata extracted by LEStrADE.',
        action: 'next-click',
        onEnter: (store) => {
            this._setFirstTimelineVisible(store, true)
            this._clearSearch()
            this._forceExpandFirstRow()
            this._closeAllMenus()
        },
        onLeave: (store) => {
            this._forceExpandFirstRow()
        }
      },
      {
        id: 'OPEN_TAG_MENU',
        view: 'explore',
        visibleElements: ['#tsEventTable tbody tr:first-child', '#tsEventTable tr.v-data-table__expanded__content'],
        clickableElement: '#tsEventTable tbody tr:first-child .v-icon[title*="Modify tags"]',
        title: 'Tagging',
        content: 'You can tag events to categorize them. Click the tag icon to open the tagging menu.',
        action: 'tag-menu-opened',
        onEnter: (store) => {
            this._setFirstTimelineVisible(store, true)
            this._clearSearch()
            this._forceExpandFirstRow()
            this._closeAllMenus()
            // Wipe tags here too to ensure a clean slate for the tagging interaction
            this._clearAllTags(store).catch(e => console.error(e))
        },
        onLeave: (store) => {
            this._forceExpandFirstRow()
            this._forceOpenTagMenu()
        }
      },
      {
        id: 'ADD_TAG',
        view: 'explore',
        visibleElements: ['#tsEventTable tbody tr:first-child', '#tsEventTable tr.v-data-table__expanded__content', '.menuable__content__active'],
        clickableElement: '.menuable__content__active .v-chip:first-child',
        title: 'Add a Tag',
        content: 'Choose a "quick tag" like "bad" to instantly label this event.',
        action: 'tag-added',
        onEnter: (store) => {
            this._setFirstTimelineVisible(store, true)
            this._clearSearch()
            this._forceExpandFirstRow()
            this._clearAllTags(store).then(() => this._forceOpenTagMenu()).catch(e => console.error(e))
        },
        onLeave: (store) => {
            this._closeAllMenus()
            this._forceExpandFirstRow()
            // Force the tag state so arrow navigation shows the same result as clicking
            this._addSampleTag(store).catch(e => console.error(e))
        }
      },
      {
        id: 'VIEW_TAGGED_DATA',
        view: 'explore',
        visibleElements: ['#tsEventTable tbody tr:first-child', '#tsEventTable tr.v-data-table__expanded__content'],
        title: 'Tag Saved',
        content: 'The tag is now saved! You can see it appearing on the event row and in the expanded details.',
        action: 'next-click',
        onEnter: (store) => {
            this._setFirstTimelineVisible(store, true)
            this._clearSearch()
            this._forceExpandFirstRow()
            this._closeAllMenus()
            // force apply the tag
            this._addSampleTag(store).catch(e => console.error(e))
        },
        onLeave: (store) => {
            this._forceCollapseAllRows()
            this._clearSearch()
        }
      },
      {
        id: 'CONGRATS',
        view: 'explore',
        visibleElements: 'body',
        title: 'Great Job!',
        content: 'You\'ve successfully explored the core features of LEStrADE. You are now ready to begin your own investigation.',
        finishButtonText: 'UPLOAD YOUR DATA',
        action: 'complete',
        onEnter: (store) => {
            this._clearSearch()
            this._forceCollapseAllRows()
            this._closeAllMenus()
        }
      }
    ]
  }

  start(store) {
    if (this.store) {
        if (!this.currentStepId) this.runStep('WELCOME')
        return
    }

    console.log('[DemoController] Initializing start sequence...');
    this.store = store

    this.onStart(this.store)

    this._setupActionListeners()

    // auto-cleanup if demoMode is turned off in store (e.g. via router navigation)
    this._storeUnsubscribe = this.store.subscribe((mutation) => {
      if (mutation.type === 'SET_DEMO_MODE' && mutation.payload === false) {
        console.log('[DemoController] demoMode disabled in store, completing demo');
        this.complete()
      }
    })

    this.runStep('WELCOME')
  }

  onStart(store) {
      this._setAllTimelinesVisible(store)
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

      console.log(`[DemoController] Action received: ${actionType} (current step: ${this.currentStepId})`);

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


  runStep(stepId) {
    const allSteps = this.getStepDefinitions()
  
    if (this.currentStepId) {
        const currentDef = allSteps.find(s => s.id === this.currentStepId)
        if (currentDef && currentDef.onLeave && this.store) {
            console.log(`[DemoController] Executing onLeave for ${this.currentStepId}`);
            currentDef.onLeave(this.store)
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
          console.log(`[DemoController] Executing onEnter for ${stepId}`);
          stepDef.onEnter(this.store)
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
    console.log('[DemoController] First step broadcasted.');
  }

  getCurrentUiState() {
      return this._lastUiUpdate
  }

  complete() {
    const wasCongrats = this.currentStepId === 'CONGRATS'
    console.log('[DemoController] Demo complete/exited');
    this._lastUiUpdate = null
    EventBus.$emit('demo:update-ui', null) // close overlay
    
    if (this.store) {
      this.store.commit('SET_DEMO_IN_PROGRESS', false)
      this.store.commit('SET_DEMO_STEP', 0)
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

    if (wasCongrats) {
        router.push({ name: 'Explore' })
    }
  }

  // --- Helper Methods ---

  _setFirstTimelineVisible(store, isVisible) {
    const firstTl = store.state.sketch.timelines[0]
    if (!firstTl) return
    
    const isCurrentlyVisible = store.state.enabledTimelines.includes(firstTl.id)
    if (isVisible && !isCurrentlyVisible) {
      store.commit('ADD_ENABLED_TIMELINES', [firstTl.id])
    } else if (!isVisible && isCurrentlyVisible) {
      store.commit('REMOVE_ENABLED_TIMELINES', [firstTl.id])
    }
  }

  _setAllTimelinesVisible(store) {
    const allTlIds = store.state.sketch.timelines.map(t => t.id)
    if (allTlIds.length > 0) {
      store.commit('SET_ENABLED_TIMELINES', allTlIds)
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
      console.log('[DemoController] Magically clearing search filters');
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
      console.log('[DemoController] Wiping all tags for fresh demo');
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
              console.log('[DemoController] Forcing tag menu open');
              this._secureClick('#tsEventTable tbody tr:first-child .v-icon[title*="Modify tags"]')
          }
      }, 100)
  }

  async _addSampleTag(store) {
      console.log('[DemoController] Programmatically adding sample tag');
      const DB = require('@/database/index.js').default
      const result = await DB.searchEvents('', { size: 1, order: 'asc' })
      if (result.objects && result.objects.length > 0) {
          const targetEvent = result.objects[0]
          await DB.updateEventTags(targetEvent._id, ['bad'])
          
          setTimeout(() => {
              EventBus.$emit('setQueryAndFilter', { doSearch: true })
          }, 50)
      }
  }

  _forceApplySampleFilter() {
      console.log('[DemoController] Forcing sample filter for result step');
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
