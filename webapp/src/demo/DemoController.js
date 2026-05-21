import router from '@/router.js'
import EventBus from '@/event-bus.js'

/**
 * DemoController orchestrates the interactive demo experience.
 * It coordinates between the Vue components (triggers), the DemoOverlay (visuals),
 * and the application state (progress).
 */
class DemoController {
  constructor() {
    this.currentStepId = null
    this.store = null
    this._actionListener = null
  }

  /**
   * Defines the step-by-step narrative of the demo.
   */
  getStepDefinitions() {
    return [
      {
        id: 'WELCOME',
        view: 'explore',
        visibleElements: 'body',
        title: 'Welcome',
        content: 'This demo will walk you through the core features of LEStrADE using sample Instagram activity.',
        action: 'next-click',
        onLeave: (store) => this._setAllTimelinesVisible(store)
      },
      {
        id: 'OPEN_TIMELINE_MENU',
        view: 'explore',
        visibleElements: '.timeline-chip:first-child',
        clickableElement: '#tsTimelineChipMenu',
        title: 'Timeline Visibility',
        content: 'Each chip represents a different data export you\'ve uploaded. Let\'s start by opening the menu.',
        action: 'timeline-menu-opened',
        onEnter: (store) => this._setAllTimelinesVisible(store)
      },
      {
        id: 'HIDE_TIMELINE_DATA',
        view: 'explore',
        visibleElements: ['.timeline-chip:first-child', '.menuable__content__active'],
        clickableElement: '#tsTimelineVisibilityToggle',
        title: 'Data Export Visibility',
        content: 'You can temporarily hide this export to focus on other data. Try toggling it off and on.',
        action: 'timeline-toggled',
        onEnter: (store) => this._setFirstTimelineVisible(store, true),
        onLeave: (store) => this._setFirstTimelineVisible(store, false)
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
        onEnter: (store) => this._setFirstTimelineVisible(store, false),
        onLeave: (store) => this._setFirstTimelineVisible(store, true)
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
        onEnter: (store) => this._setFirstTimelineVisible(store, true),
        onLeave: (store) => this._setFirstTimelineVisible(store, true)
      },

      {
        id: 'CONGRATS',
        view: 'explore',
        visibleElements: 'body',
        title: 'Great Job!',
        content: 'You\'ve successfully toggled the data visibility. We can add more steps for expanding events, filtering, and tagging next. Ready to see the full demo?',
        action: 'complete'
      }
    ]
  }

  /**
   * Starts the demo from the Explore view.
   */
  start(store) {
    if (this.store) {
        // If already started, ensure we are on a valid step
        if (!this.currentStepId) this.runStep('WELCOME')
        return
    }

    console.log('[DemoController] Starting interactive demo');
    this.store = store

    // Global onStart hook
    this.onStart(this.store)

    this._setupActionListeners()

    // Auto-cleanup if demoMode is turned off in store (e.g. via router navigation)
    this._storeUnsubscribe = this.store.subscribe((mutation) => {
      if (mutation.type === 'SET_DEMO_MODE' && mutation.payload === false) {
        console.log('[DemoController] demoMode disabled in store, completing demo');
        this.complete()
      }
    })

    this.runStep('WELCOME')
  }

  /**
   * Optional global setup logic that runs once when the demo begins.
   */
  onStart(store) {
      this._setAllTimelinesVisible(store)
  }

  /**
   * Sets up listeners for user actions emitted by components.
   */
  _setupActionListeners() {
    if (this._actionListener) {
      EventBus.$off('demo:action', this._actionListener)
    }
    
    this._actionListener = (actionType) => {
      const allSteps = this.getStepDefinitions()
      const currentStepDef = allSteps.find(s => s.id === this.currentStepId)
      if (!currentStepDef) return

      console.log(`[DemoController] Action received: ${actionType} (current step: ${this.currentStepId})`);

      // Navigation overrides
      if (actionType === 'next-click' || actionType === 'prev-click') {
          if (actionType === 'next-click') this.moveNext()
          else this.movePrevious()
          return
      }

      // Action-driven progression
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

  /**
   * Executes a specific step, updating both state and UI.
   */
  runStep(stepId) {
    const allSteps = this.getStepDefinitions()
    
    // Execute onLeave hook of current step
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
      
      // Execute onEnter hook of new step
      if (stepDef.onEnter) {
          console.log(`[DemoController] Executing onEnter for ${stepId}`);
          stepDef.onEnter(this.store)
      }
    }

    // Update the visual overlay
    EventBus.$emit('demo:update-ui', {
      id: stepDef.id,
      title: stepDef.title,
      content: stepDef.content,
      visibleElements: stepDef.visibleElements === 'body' ? undefined : stepDef.visibleElements,
      clickableElement: stepDef.clickableElement,
      blockedElements: stepDef.blockedElements,
      arrowPosition: stepDef.arrowPosition,
      isFirst: stepIndex === 0,
      isLast: stepIndex === allSteps.length - 1,
      stepNumber: stepNumber,
      totalSteps: allSteps.length
    })
  }

  /**
   * Cleans up the demo state and closes the overlay.
   */
  complete() {
    console.log('[DemoController] Demo complete/exited');
    EventBus.$emit('demo:update-ui', null) // Close overlay
    
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
}

export default new DemoController()
