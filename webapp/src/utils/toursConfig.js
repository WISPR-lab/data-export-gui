function getMainViewsTourSteps() {
  return [
    {
      element: '#tsMainViewsSection',
      header: 'Views',
      content: 'Switch between Events (your account activity) and Devices (what accessed your account).',
    },
  ]
}

function getTimelineSelectionTourSteps() {
  return [
    {
      element: '#tsTimelinePicker',
      header: 'Select Data Exports',
      content: 'Toggle the visibility of each data export in your search results',
    },
  ]
}

function getTimelineCustomizationTourSteps() {
  return [
    {
      element: '#tsTimelineChipMenu',
      header: 'Rename & Customize',
      content: 'Click the menu button to rename your data export or change its display color for easier identification.',
    },
  ]
}

function getSearchTourSteps() {
  return [
    {
      element: '#tsSearchInput',
      header: 'Search Your Events',
      content: 'Search through events and account activity via keywords. Press Enter to search, or use the help icon (?) to learn more about advanced syntax.',
    },
  ]
}

function getSelectColumnsTourSteps() {
  return [
    {
      element: '#tsModifyColumnsBtn',
      header: 'Select Visible Columns',
      content: 'Customize which columns are displayed in the event table.',
    },
  ]
}

function getEventDetailsTourSteps() {
  return [
    {
      element: '#tsEventList tbody tr:first-child',
      header: 'View Event Details',
      content: 'Click on any event to expand it and view the full details, including timestamps, sources, and additional metadata.',
    },
  ]
}

function getFlagsAndStarsTourSteps() {
  return [
    {
      element: '#tsEventList tbody tr:first-child #tsAnnotateActions',
      header: 'Annotate & Flag',
      content: 'Star or create tags to mark important events for quick reference.',
    },
  ]
}

export function getCombinedTourSteps() {
  return [
    ...getMainViewsTourSteps(),
    ...getTimelineSelectionTourSteps(),
    ...getTimelineCustomizationTourSteps(),
    ...getSearchTourSteps(),
    ...getSelectColumnsTourSteps(),
    ...getEventDetailsTourSteps(),
    ...getFlagsAndStarsTourSteps(),
  ]
}

export {
  getMainViewsTourSteps,
  getTimelineSelectionTourSteps,
  getTimelineCustomizationTourSteps,
  getSearchTourSteps,
  getSelectColumnsTourSteps,
  getEventDetailsTourSteps,
  getFlagsAndStarsTourSteps,
}

