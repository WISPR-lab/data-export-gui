const TOUR_KEYS = {
  EXPLORE_MAIN_VIEWS_TOUR: 'exploreMainViewsTourCompleted',
  EXPLORE_SEARCH_TOUR: 'exploreSearchTourCompleted',
};

const TOUR_SEQUENCE = [
  TOUR_KEYS.EXPLORE_MAIN_VIEWS_TOUR,
  TOUR_KEYS.EXPLORE_SEARCH_TOUR,
];

export function isTourCompleted(tourKey) {
  try {
    const state = JSON.parse(localStorage.getItem('tourState') || '{}');
    return state[tourKey] === true;
  } catch {
    return false;
  }
}

export function shouldShowTour(tourKey) {
  if (isTourCompleted(tourKey)) return false;
  const tourIndex = TOUR_SEQUENCE.indexOf(tourKey);
  if (tourIndex === -1) return false;
  
  // Show this tour only if all previous tours are completed
  for (let i = 0; i < tourIndex; i++) {
    if (!isTourCompleted(TOUR_SEQUENCE[i])) {
      return false;
    }
  }
  return true;
}

export function completeTour(tourKey) {
  try {
    const state = JSON.parse(localStorage.getItem('tourState') || '{}');
    state[tourKey] = true;
    state.lastTourCompleted = Date.now();
    localStorage.setItem('tourState', JSON.stringify(state));
    
    // Notify any listeners that tours may need to update
    window.dispatchEvent(new CustomEvent('tourCompleted', { detail: { tourKey } }));
  } catch (e) {
    console.warn('Failed to save tour state:', e);
  }
}

export function resetTour(tourKey) {
  try {
    const state = JSON.parse(localStorage.getItem('tourState') || '{}');
    delete state[tourKey];
    localStorage.setItem('tourState', JSON.stringify(state));
  } catch (e) {
    console.warn('Failed to reset tour:', e);
  }
}

export { TOUR_KEYS };
