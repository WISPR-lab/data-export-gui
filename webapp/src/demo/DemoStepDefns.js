import EventBus from '@/event-bus.js'

export const getStepDefinitions = () => [
  {
    id: 'WELCOME',
    view: 'explore',
    visibleElements: 'body',
    title: 'Interactive Demo',
    content: 'This demo will walk you through the core features of LEStrADE using sample data. \n\n (Tip: You can use the ← and → keys to navigate)',
    action: 'next-click',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        await controller._clearAllTags(store).catch(e => console.error(e))
    }
  },
  {
    id: 'OPEN_TIMELINE_MENU',
    view: 'explore',
    visibleElements: '.timeline-chip:first-child',
    clickableElement: '#tsTimelineChipMenu',
    title: 'Data Export Visibility',
    content: 'Each chip represents a different data export you\'ve uploaded. Let\'s start by opening the menu.',
    action: 'timeline-menu-opened',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        await controller._clearAllTags(store).catch(e => console.error(e))
    }
  },
  {
    id: 'HIDE_TIMELINE_DATA',
    view: 'explore',
    visibleElements: ['.timeline-chip:first-child', '.menuable__content__active'],
    clickableElement: '#tsTimelineVisibilityToggle',
    title: 'Data Export Visibility',
    content: 'You can temporarily hide this export to focus on other data.',
    action: 'timeline-toggled',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        await controller._clearAllTags(store).catch(e => console.error(e))
        // Ensure menu is open if they skipped to here
        const menuVisible = document.querySelector('.menuable__content__active')
        if (!menuVisible) {
            controller._secureClick('#tsTimelineChipMenu')
        }
    }
  },
  {
    id: 'SHOW_TIMELINE_DATA',
    view: 'explore',
    visibleElements: '.timeline-chip:first-child',
    clickableElement: '.timeline-chip:first-child',
    blockedElements: ['#tsTimelineChipMenu'],
    title: 'Data Export Visibility',
    content: 'You can bring it back anytime by clicking on the chip. Try re-enabling it.',
    action: 'timeline-toggled',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        await controller._clearAllTags(store).catch(e => console.error(e))
        controller._setFirstTimelineVisible(store, false)
    }
  },
  {
    id: 'SHOW_TIMELINE_DATA2',
    view: 'explore',
    visibleElements: '.timeline-chip:first-child',
    clickableElement: '',
    blockedElements: ['#tsTimelineChipMenu', '.timeline-chip:first-child'],
    title: 'Data Export Visibility',
    content: 'Done! Let\'s take a closer look at your data.',
    action: 'next-click',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        await controller._clearAllTags(store).catch(e => console.error(e))
    }
  },
  {
    id: 'EVENTS_MACRO',
    view: 'explore',
    visibleElements: '#tsEventTable',
    title: 'Events View',
    content: 'This table shows every "event" or user action extracted from your data exports, sorted chronologically.',
    action: 'next-click',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        await controller._clearAllTags(store).catch(e => console.error(e))
    }
  },
  {
    id: 'EXPAND_EVENT',
    view: 'explore',
    visibleElements: '#tsEventTable tbody tr:first-child',
    clickableElement: '#tsEventTable tbody tr:first-child',
    title: 'Events View',
    content: 'Click on any event row to see more details about it.',
    action: 'event-expanded',
    onEnter: async (controller, store, isForward) => {
        controller._setFirstTimelineVisible(store, true)
        controller._clearSearch()
        controller._forceCollapseAllRows()
        controller._closeAllMenus()
        await controller._clearAllTags(store).catch(e => console.error(e))
    }
  },
  {
    id: 'READ_EVENT_DETAILS',
    view: 'explore',
    visibleElements: ['#tsEventTable tbody tr:first-child', '#tsEventTable tr.v-data-table__expanded__content'],
    title: 'Events View',
    content: 'Click on any event row to see more details about it.',
    action: 'next-click',
    onEnter: async (controller, store, isForward) => {
        controller._setFirstTimelineVisible(store, true)
        controller._clearSearch()
        controller._forceExpandFirstRow()
        controller._closeAllMenus()
        await controller._clearAllTags(store).catch(e => console.error(e))
    }
  },
  {
    id: 'OPEN_TAG_MENU',
    view: 'explore',
    visibleElements: ['#tsEventTable tbody tr:first-child', '#tsEventTable tr.v-data-table__expanded__content'],
    clickableElement: '#tsEventTable tbody tr:first-child .v-icon[title*="Modify tags"]',
    title: 'Tagging Events',
    content: 'You can add pre-defined or custom labels to events. Try adding a tag to this one.',
    action: 'tag-menu-opened',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        await controller._clearAllTags(store).catch(e => console.error(e))
        controller._forceExpandFirstRow()
    }
  },
  {
    id: 'ADD_TAG',
    view: 'explore',
    visibleElements: ['#tsEventTable tbody tr:first-child', '#tsEventTable tr.v-data-table__expanded__content', '.menuable__content__active'],
    clickableElement: '.menuable__content__active .v-chip:first-child',
    title: 'Tagging Events',
    content: 'You can add pre-defined or custom labels to events. Try adding a tag to this one.',
    action: 'tag-added',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        await controller._clearAllTags(store).catch(e => console.error(e))
        controller._forceExpandFirstRow()
        controller._forceOpenTagMenu()
    }
  },
  {
    id: 'VIEW_TAGGED_DATA',
    view: 'explore',
    visibleElements: ['#tsEventTable tbody tr:first-child', '#tsEventTable tr.v-data-table__expanded__content'],
    title: 'Tagging Events',
    content: 'Great job!',
    action: 'next-click',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        controller._forceExpandFirstRow()
        await controller._addSampleTag(store).catch(e => console.error(e))
    }
  },
  {
    id: 'SIDEBAR_TAGS',
    view: 'explore',
    visibleElements: '#tsLeftPanelTags',
    clickableElement: '#tsLeftPanelTags',
    blockedElements: ['#tsLeftPanelTags [style*="cursor: pointer"]'],
    title: 'Tagging Events',
    content: 'You can view all the tags you\'ve added by clicking the sidebar here.',
    action: 'next-click',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        EventBus.$emit('demo:collapse-event-types')
    }
  },
  {
    id: 'OPEN_EVENT_TYPES',
    view: 'explore',
    visibleElements: '#tsLeftPanelEventTypes',
    clickableElement: '#tsLeftPanelEventTypesHeader',
    blockedElements: ['#tsLeftPanelEventTypesHeader [style*="cursor: pointer"]'],
    title: 'Additional Filters',
    content: 'You can also filter events by type. Try it out!',
    action: 'event-types-expanded',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        EventBus.$emit('demo:collapse-event-types')
    }
  },
  {
    id: 'FILTER_EVENT_TYPE',
    view: 'explore',
    visibleElements: '#tsLeftPanelEventTypes',
    clickableElement: '#tsLeftPanelEventTypesList div[style*="cursor: pointer"]:last-child',
    title: 'Additional Filters',
    content: 'You can also filter events by type. Try it out!',
    action: 'event-type-clicked',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        if (!isForward) {
            // When going backwards, ensure types are expanded
            EventBus.$emit('demo:expand-event-types')
        }
    }
  },
  {
    id: 'EVENT_LIST_FILTERED',
    view: 'explore',
    visibleElements: '#tsEventTable',
    title: 'Additional Filters',
    content: 'Great job! Now we see only login events.',
    action: 'next-click',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        EventBus.$emit('demo:expand-event-types')
        EventBus.$emit('setQueryAndFilter', {
            queryString: 'message:"Successful login"',
            doSearch: true
        })
    }
  },
  {
    id: 'HIGHLIGHT_SEARCH_BAR',
    view: 'explore',
    visibleElements: '#tsSearchBar',
    title: 'Search Bar',
    content: 'Notice that this pre-populated a query in the search bar.',
    action: 'next-click',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        EventBus.$emit('setQueryAndFilter', {
            queryString: 'message:"Successful login"',
            doSearch: true
        })
    }
  },
  {
    id: 'SEARCH_DSL_HELP',
    view: 'explore',
    visibleElements: '#tsSearchHelpButton',
    // clickableElement: '#tsSearchHelpButton',
    title: 'Search Bar',
    content: 'You can learn more about supported search filters and syntax here.',
    action: 'next-click',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
        EventBus.$emit('setQueryAndFilter', {
            queryString: 'message:"Successful login"',
            doSearch: true
        })
    }
  },
  {
    id: 'TIME_FILTER',
    view: 'explore',
    visibleElements: '#tsAddTimefilterButton',
    title: 'Time Filters',
    content: 'Use time filters to restrict your queries to a precise time range.',
    action: 'next-click',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
    }
  },
  {
    id: 'EVENTS_VIEW_COMPLETE',
    view: 'explore',
    visibleElements: 'body',
    title: 'Congrats!',
    content: "You've successfully learned how to use the Events View.",
    action: 'next-click',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
    }
  },
  {
    id: 'DEVICES_VIEW_DEMO_SOON',
    view: 'explore',
    visibleElements: '#tsNavigationDevices',
    title: 'Devices View',
    content: 'This button will take you to the Devices View, where you can analyze your data by device rather than chronologically. A guided tour is coming soon, but feel free to click on it and explore around after uploading your own data.',
    action: 'next-click',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
    }
  },
  {
    id: 'FINISH',
    view: 'explore',
    visibleElements: '#tsTutorialsButton',
    title: 'Finish',
    content: 'You can redo this demo again by navigating to Tutorials.', // TODO add interactive button
    finishButtonText: 'FINISH',
    action: 'complete',
    onEnter: async (controller, store, isForward) => {
        await controller.basicInitialize(store)
    }
  }
]
