import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'
import router from '@/router.js'
import EventBus from '@/event-bus.js'

class DemoWalkthrough {
  constructor() {
    this.driverInstance = null
    this.currentStep = 0
    this.store = null
    this._actionListener = null
    this._visibilityToggles = 0 // Track off/on cycles for timeline step
  }

  getStepDefinitions() {
    return [
      {
        step: 1,
        view: 'explore',
        element: 'body',
        title: 'Welcome!',
        content: 'This demo will walk you through the core features of LEStrADE using sample Instagram activity. Click "Next" to begin.',
        action: 'next-click'
      },
      {
        step: 2,
        view: 'explore',
        element: '#tsTimelineChipMenu',
        title: 'Your Data Exports',
        content: 'Each chip represents a different data export you\'ve uploaded. Let\'s start by opening the menu.',
        action: 'timeline-menu-opened'
      },
      {
        step: 3,
        view: 'explore',
        element: '#tsTimelineVisibilityToggle',
        title: 'Data Export Visibility',
        content: 'You can temporarily hide this export to focus on other data. Try togggling it off and on.',
        action: 'timeline-visibility-restored'
      },
      {
        step: 4,
        view: 'explore',
        element: '.v-data-table tbody tr:first-child',
        title: 'Expanding Events',
        content: 'Click on any event in the table to expand it and see all the underlying details.',
        action: 'event-expanded'
      },
      {
        step: 5,
        view: 'explore',
        element: '.v-data-table .v-expanded-content .v-btn:first-child',
        title: 'Focus with Filters',
        content: 'See a value you want to investigate? Click the filter icon next to it to instantly focus on similar activity.',
        action: 'inline-filter-clicked'
      },
      {
        step: 6,
        view: 'explore',
        element: '.v-data-table tbody tr:first-child #tsAnnotateActions .v-btn:nth-child(2)',
        title: 'Categorize with Tags',
        content: 'You can label events with tags to organize your findings. Click the tag icon to add one.',
        action: 'tag-added'
      },
      {
        step: 7,
        view: 'explore',
        element: '#tsLeftPanelSavedSearches',
        title: 'Shortcuts',
        content: 'The left panel stores your tags and common filters. Click on a saved search to run it automatically.',
        action: 'saved-search-clicked'
      },
      {
        step: 8,
        view: 'explore',
        element: '#tsSearchInput',
        title: 'Direct Search',
        content: 'You can also search directly for any term. Type "login" and press Enter to see all related events.',
        action: 'search-executed'
      },
      {
        step: 9,
        view: 'explore',
        element: '#tsNavigationDevices',
        title: 'Device Analysis',
        content: 'Lestrade also analyzes the devices used to access your account. Click "Devices" to see the breakdown.',
        action: 'route-changed-devices'
      },
      {
        step: 10,
        view: 'devices',
        element: '.devices-list .v-expansion-panel:first-child .v-expansion-panel-header',
        title: 'Device Details',
        content: 'Expand a device profile to see specific technical details like operating system and browser versions.',
        action: 'device-expanded'
      },
      {
        step: 11,
        view: 'devices',
        element: '.blue-grey.lighten-5:first-child',
        title: 'Link Activity',
        content: 'Unassigned sessions can be manually linked. Drag and drop this session onto a device profile above to merge them.',
        action: 'device-dropped'
      },
      {
        step: 12,
        view: 'devices',
        element: '.interactive-demo-link',
        title: 'Tutorial Complete',
        content: 'You are now ready to analyze your own data. You can restart this tour anytime from this menu.',
        action: 'complete'
      }
    ]
  }

  startExplore(store) {
    this.store = store
    this._visibilityToggles = 0
    this._setupActionListeners()
    this.runStep(1)
  }

  resumeDevices(store) {
    this.store = store
    this._setupActionListeners()
    this.runStep(10)
  }

  _setupActionListeners() {
    if (this._actionListener) {
      EventBus.$off('demo-action', this._actionListener)
    }
    
    this._actionListener = (actionType) => {
      const allSteps = this.getStepDefinitions()
      const currentStepDef = allSteps.find(s => s.step === this.currentStep)
      
      if (!currentStepDef) return

      if (actionType === 'timeline-toggled' && this.currentStep === 3) {
        this._visibilityToggles++
        // We want 1 for OFF and then 2 for back ON
        if (this._visibilityToggles >= 2) {
          this.moveNext()
        }
        return
      }
      
      if (currentStepDef.action === actionType || (actionType === 'route-changed-devices' && this.currentStep === 9)) {
        console.log(`[DemoWalkthrough] Action received: ${actionType}. Advancing.`);
        
        if (actionType === 'inline-filter-clicked') {
          setTimeout(() => this.moveNext(), 1500)
        } else if (actionType === 'complete') {
          this.complete()
        } else {
          this.moveNext()
        }
      }
    }
    
    EventBus.$on('demo-action', this._actionListener)
  }

  moveNext() {
    const nextStep = this.currentStep + 1
    const allSteps = this.getStepDefinitions()
    const nextStepDef = allSteps.find(s => s.step === nextStep)

    if (!nextStepDef) {
      this.complete()
      return
    }

    const currentView = this.$getCurrentView()
    if (nextStepDef.view !== currentView) {
      this.close()
      // Note: Component mounts/watchers in the new view will call resumeDevices/startExplore
      return
    }

    this.runStep(nextStep)
  }

  movePrevious() {
    const prevStep = this.currentStep - 1
    const allSteps = this.getStepDefinitions()
    const prevStepDef = allSteps.find(s => s.step === prevStep)

    if (!prevStepDef) return

    const currentView = this.$getCurrentView()
    if (prevStepDef.view !== currentView) {
        this.close()
        // Handle navigation across views manually if needed, but for now assuming same view
        if (prevStepDef.view === 'explore') {
            router.push('/demo/explore')
        } else if (prevStepDef.view === 'devices') {
            router.push('/demo/devices')
        }
        return
    }

    this.runStep(prevStep)
  }

  runStep(stepNumber) {
    const allSteps = this.getStepDefinitions()
    const stepDef = allSteps.find(s => s.step === stepNumber)
    
    if (!stepDef) return

    this.currentStep = stepNumber
    if (this.store) {
      this.store.commit('SET_TOUR_CURRENT_STEP', stepNumber)
    }

    const isFirstStep = stepNumber === 1
    const isLastStep = stepNumber === allSteps.length

    this.driverInstance = driver({
      showProgress: true,
      allowClose: false,
      overlayClickAction: 'none',
      overlayOpacity: 0.5,
      onDeselected: () => {},
      steps: [
        {
          element: stepDef.element === 'body' ? undefined : stepDef.element,
          popover: {
            title: stepDef.title,
            description: stepDef.content,
            side: stepDef.element === 'body' ? "over" : "bottom",
            align: 'start',
            showButtons: ['next', 'previous'],
            onNextClick: () => {
                if (isLastStep) {
                    this.complete()
                } else {
                    this.moveNext()
                }
            },
            onPrevClick: () => {
                this.movePrevious()
            }
          }
        }
      ]
    })

    this.driverInstance.drive()
  }

  $getCurrentView() {
    const routeName = router.currentRoute.name
    if (routeName === 'Explore' || routeName === 'DemoExplore') return 'explore'
    if (routeName === 'Devices' || routeName === 'DemoDevices') return 'devices'
    return 'unknown'
  }

  complete() {
    this.close()
    if (this.store) {
      this.store.commit('SET_TOUR_IN_PROGRESS', false)
      this.store.commit('SET_TOUR_CURRENT_STEP', 0)
    }
    if (this._actionListener) {
      EventBus.$off('demo-action', this._actionListener)
      this._actionListener = null
    }
  }

  close() {
    if (this.driverInstance) {
      this.driverInstance.destroy()
      this.driverInstance = null
    }
  }
}

export default new DemoWalkthrough()
