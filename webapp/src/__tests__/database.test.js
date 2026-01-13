/**
 * BrowserDB tests
 * 
 * npm test -- database.test.js
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import BrowserDB from '../database.js'


describe('Database CRUD Operations', () => {
  beforeEach(async () => {
    // TODO
  })

  afterEach(async () => {
    // TODO clean up test data
  })

  describe('Sketches', () => {
    it('should create a sketch', async () => {
      const sketchData = {
        name: 'Test Sketch',
        description: 'Test Description',
        user_id: 'test-user',
      }
      
      const response = await BrowserDB.createSketch(sketchData)
      
      expect(response.data.objects).toHaveLength(1)
      expect(response.data.objects[0].name).toBe('Test Sketch')
      expect(response.data.objects[0].id).toBeDefined()
    })

    it('should retrieve a sketch by ID', async () => {
      const sketchData = {
        name: 'Retrieve Test',
        description: 'Test',
        user_id: 'test-user',
      }
      
      const createResponse = await BrowserDB.createSketch(sketchData)
      const sketchId = createResponse.data.objects[0].id
      
      const getResponse = await BrowserDB.getSketch(sketchId)
      
      expect(getResponse.data.objects[0].id).toBe(sketchId)
      expect(getResponse.data.objects[0].name).toBe('Retrieve Test')
    })

    it('should list all sketches', async () => {
      const response = await BrowserDB.getSketchList()
      
      expect(response.data.objects).toBeDefined()
      expect(Array.isArray(response.data.objects)).toBe(true)
      expect(response.data.meta.total_items).toBeDefined()
    })

    it('should update a sketch', async () => {
      const sketchData = {
        name: 'Update Test',
        description: 'Original',
        user_id: 'test-user',
      }
      
      const createResponse = await BrowserDB.createSketch(sketchData)
      const sketchId = createResponse.data.objects[0].id
      
      const updateResponse = await BrowserDB.updateSketch(sketchId, {
        description: 'Updated',
      })
      
      expect(updateResponse.data.objects[0].description).toBe('Updated')
    })

    it('should delete a sketch', async () => {
      const sketchData = {
        name: 'Delete Test',
        description: 'Test',
        user_id: 'test-user',
      }
      
      const createResponse = await BrowserDB.createSketch(sketchData)
      const sketchId = createResponse.data.objects[0].id
      
      await BrowserDB.deleteSketch(sketchId)
      
      const getResponse = await BrowserDB.getSketch(sketchId)
      expect(getResponse.data.objects[0]).toBeUndefined()
    })
  })

  describe('Timelines', () => {
    let sketchId

    beforeEach(async () => {
      const sketch = await BrowserDB.createSketch({
        name: 'Timeline Test',
        user_id: 'test-user',
      })
      sketchId = sketch.data.objects[0].id
    })

    it('should create a timeline', async () => {
      const timelineData = {
        name: 'Test Timeline',
        sketch_id: sketchId,
        description: 'Test',
      }
      
      const response = await BrowserDB.createTimeline(timelineData)
      
      expect(response.data.objects).toHaveLength(1)
      expect(response.data.objects[0].name).toBe('Test Timeline')
      expect(response.data.objects[0].sketch_id).toBe(sketchId)
    })

    it('should retrieve timelines for a sketch', async () => {
      await BrowserDB.createTimeline({
        name: 'Timeline 1',
        sketch_id: sketchId,
      })
      
      const response = await BrowserDB.getTimelines(sketchId)
      
      expect(Array.isArray(response.data.objects)).toBe(true)
      expect(response.data.objects.length).toBeGreaterThan(0)
    })
  })

  describe('Events', () => {
    let sketchId, timelineId

    beforeEach(async () => {
      const sketch = await BrowserDB.createSketch({
        name: 'Event Test',
        user_id: 'test-user',
      })
      sketchId = sketch.data.objects[0].id

      const timeline = await BrowserDB.createTimeline({
        name: 'Event Timeline',
        sketch_id: sketchId,
      })
      timelineId = timeline.data.objects[0].id
    })

    it('should create an event', async () => {
      const eventData = {
        sketch_id: sketchId,
        timeline_id: timelineId,
        timestamp: Math.floor(Date.now() / 1000),
        message: 'Test Event',
        data_type: 'test_event',
      }
      
      const response = await BrowserDB.createEvent(eventData)
      
      expect(response.data.objects).toHaveLength(1)
      expect(response.data.objects[0].message).toBe('Test Event')
    })

    it('should retrieve events for a timeline', async () => {
      await BrowserDB.createEvent({
        sketch_id: sketchId,
        timeline_id: timelineId,
        timestamp: Math.floor(Date.now() / 1000),
        message: 'Test Event',
        data_type: 'test_event',
      })
      
      const response = await BrowserDB.getTimelineEvents(timelineId)
      
      expect(Array.isArray(response.data.objects)).toBe(true)
    })

    it('should search events', async () => {
      await BrowserDB.createEvent({
        sketch_id: sketchId,
        timeline_id: timelineId,
        timestamp: Math.floor(Date.now() / 1000),
        message: 'Searchable Event',
        data_type: 'test_event',
      })
      
      const response = await BrowserDB.searchEvents(sketchId, 'Searchable')
      
      expect(response.data.objects.length).toBeGreaterThan(0)
      expect(response.data.objects[0].message).toContain('Searchable')
    })
  })

  describe('Tags and Annotations', () => {
    let sketchId, eventId

    beforeEach(async () => {
      const sketch = await BrowserDB.createSketch({
        name: 'Tag Test',
        user_id: 'test-user',
      })
      sketchId = sketch.data.objects[0].id

      const event = await BrowserDB.createEvent({
        sketch_id: sketchId,
        timestamp: Math.floor(Date.now() / 1000),
        message: 'Tag Test Event',
        data_type: 'test_event',
      })
      eventId = event.data.objects[0].id
    })

    it('should tag an event', async () => {
      const response = await BrowserDB.tagObjects('event', [eventId], ['malware', 'suspicious'])
      
      expect(response.data.objects).toBeDefined()
    })

    it('should remove tags from an event', async () => {
      await BrowserDB.tagObjects('event', [eventId], ['malware'])
      const response = await BrowserDB.untagObjects('event', [eventId], ['malware'])
      
      expect(response.data.objects).toBeDefined()
    })

    it('should save an annotation', async () => {
      const annotationData = {
        sketch_id: sketchId,
        event_id: eventId,
        annotation_type: 'comment',
        content: 'Test comment',
      }
      
      const response = await BrowserDB.saveAnnotation(annotationData)
      
      expect(response.data.objects[0].content).toBe('Test comment')
    })
  })
})


describe('Response Format', () => {
  it('should return data in { data: { objects, meta } } format', async () => {
    const response = await BrowserDB.getSketchList()
    
    expect(response).toHaveProperty('data')
    expect(response.data).toHaveProperty('objects')
    expect(response.data).toHaveProperty('meta')
    expect(Array.isArray(response.data.objects)).toBe(true)
  })

  it('meta should include total_items for list endpoints', async () => {
    const response = await BrowserDB.getSketchList()
    
    expect(response.data.meta).toHaveProperty('total_items')
    expect(typeof response.data.meta.total_items).toBe('number')
  })
})
