import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'
import router from '@/router.js'

class DemoWalkthrough {
  constructor() {
    this.driverInstance = null
    this.currentStep = 0
    this.store = null
    this.onStep5Complete = null
    this.onStep7Complete = null
  }

  // Define all 7 steps - steps 1-5 are for Explore view, steps 6-7 are for Devices view
  getStepDefinitions() {
    return [
      {
        step: 1,
        view: 'explore',
        element: '#tsSearchInput',
        header: '👋 Welcome!',
        content: 'This is sample Instagram activity data. Let\'s explore it together. First, here\'s the search bar where you can find specific events.',
      },
      {
        step: 2,
        view: 'explore',
        element: '#tsTimelinePicker',
        header: '📅 Select Data Sources',
        content: 'Here you can toggle which data sources to view. Each timeline represents a different upload or account activity snapshot.',
      },
      {
        step: 3,
        view: 'explore',
        element: '.v-data-table',
        header: '📊 Event Timeline',
        content: 'This table shows your activity events. Each row is an action your account took or an event that happened to it.',
      },
      {
        step: 4,
        view: 'explore',
        element: '[data-filter-id]', // Generic selector for filters - will adjust based on actual DOM
        header: '🏷️ Filter & Tag Events',
        content: 'You can filter events by tags, labels, and other criteria. Try adding filters to focus on specific events.',
      },
      {
        step: 5,
        view: 'explore',
        element: '.v-data-table__header',
        header: '⚙️ Customize Your View',
        content: 'You can customize which columns appear in the table to show the data that matters to you. Ready to see devices next?',
      },
      {
        step: 6,
        view: 'devices',
        element: '.devices-list',
        header: '🖥️ Device Information',
        content: 'This section shows all the devices that accessed your account, including their type, OS, and browser information.',
      },
      {
        step: 7,
        view: 'devices',
        element: '.device-profile-card',
        header: '✨ You\'ve Got It!',
        content: 'Now you understand the basics. Ready to upload your own data? You\'ll be able to explore all your real account activity this way.',
      },
    ]
  }

  // Start the walkthrough from the Explore view
  startExplore(store) {
    this.store = store
    this.currentStep = 1
    this.runStep(1)
  }

  // Resume the walkthrough at step 6 in the Devices view
  resumeDevices(store) {
    this.store = store
    this.currentStep = 6
    this.runStep(6)
  }

  // Run a specific step
  runStep(stepNumber) {
    const allSteps = this.getStepDefinitions()
    const stepDef = allSteps.find(s => s.step === stepNumber)
    
    if (!stepDef) {
      console.error(`[DemoWalkthrough] Step ${stepNumber} not found`);
      return;
    }

    const currentView = this.$getCurrentView()
    if (currentView !== stepDef.view) {
      console.warn(`[DemoWalkthrough] Step ${stepNumber} is for ${stepDef.view} view, but we're in ${currentView}`);
      // Could navigate here, but for now just try to run it
    }

    this.currentStep = stepNumber
    if (this.store) {
      this.store.commit('SET_TOUR_CURRENT_STEP', stepNumber)
    }

    const handleNextClick = () => {
      if (stepNumber === 5) {
        // Navigate to devices after step 5
        this.close()
        router.push('/devices').then(() => {
          // Resume at step 6 after navigation
          this.$nextTick(() => {
            this.resumeDevices(this.store)
          })
        })
      } else if (stepNumber === 7) {
        // Complete the tour after step 7
        this.complete()
      } else {
        this.runStep(stepNumber + 1)
      }
    }

    const handlePrevClick = () => {
      if (stepNumber > 1) {
        if (stepNumber === 6) {
          // Navigate back to explore
          this.close()
          router.push('/explore').then(() => {
            this.$nextTick(() => {
              this.runStep(stepNumber - 1)
            })
          })
        } else {
          this.runStep(stepNumber - 1)
        }
      }
    }

    const handleCloseClick = () => {
      this.close()
    }

    this.driverInstance = driver({
      showProgress: true,
      steps: [
        {
          element: stepDef.element || 'body',
          popover: {
            title: stepDef.header,
            description: stepDef.content,
            showButtons: ['next', 'previous', 'close'],
            onNextClick: handleNextClick,
            onPrevClick: handlePrevClick,
            onCloseClick: handleCloseClick,
          },
        },
      ],
    })

    this.driverInstance.drive()
  }

  $getCurrentView() {
    const routeName = router.currentRoute.name
    if (routeName === 'Explore' || routeName === 'DemoExplore') return 'explore'
    if (routeName === 'Devices' || routeName === 'DemoDevices') return 'devices'
    return 'unknown'
  }

  $nextTick(callback) {
    // Simple nextTick polyfill
    setTimeout(callback, 100)
  }

  complete() {
    this.close()
    if (this.store) {
      this.store.commit('SET_TOUR_IN_PROGRESS', false)
      this.store.commit('SET_TOUR_CURRENT_STEP', 0)
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
moWalkthrough()
