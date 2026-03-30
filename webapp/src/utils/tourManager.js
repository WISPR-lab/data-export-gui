import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'

class TourManager {
  constructor() {
    this.driverInstance = null
  }

  getTourState() {
    try {
      return localStorage.getItem('tour_state') || 'no_data_uploaded'
    } catch {
      return 'no_data_uploaded'
    }
  }

  setTourState(state) {
    try {
      localStorage.setItem('tour_state', state)
    } catch (e) {
      console.warn('Could not save tour state to localStorage:', e)
    }
  }

  startTour(steps) {
    this.driverInstance = driver({
      showProgress: true,
      steps: steps.map((step) => ({
        element: step.element,
        popover: {
          title: step.header,
          description: step.content,
          showButtons: ['next', 'previous', 'close'],
          onNextClick: () => this.driverInstance.moveNext(),
          onPrevClick: () => this.driverInstance.movePrevious(),
          onCloseClick: () => this.closeTour(),
        },
      })),
    })

    this.driverInstance.drive()
  }

  closeTour() {
    if (this.driverInstance) {
      this.driverInstance.destroy()
    }
    this.setTourState('tour_completed')
  }

  resetTourState() {
    try {
      localStorage.removeItem('tour_state')
    } catch (e) {
      console.warn('Could not reset tour state:', e)
    }
  }
}

export default new TourManager()
