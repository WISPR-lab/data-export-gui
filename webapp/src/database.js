// database.js
// IndexedDB wrapper for Timesketch browser-based storage using Dexie.js

import Dexie from 'dexie';
import yaml from 'js-yaml';
import { tagMetadata } from './tag_metadata.js';



class DBTodoError extends Error {
  constructor(functionName, type = 'implement') {
    const action = type === 'deprecate' ? 'deprecate this + dependencies' : 'implement eventually';
    super(`Not implemented: ${functionName}. TODO: ${action}.`);
    this.name = 'TodoError';
    this.type = type;
  }
}

function throwTodoError(type = 'implement') {
  const err = new Error();
  const stack = err.stack.split('\n');
  const callerLine = stack[2] || '';
  const match = callerLine.match(/at (\w+)/);
  const functionName = match ? match[1] : 'unknown';
  throw new DBTodoError(functionName, type);
}

const throwTodoImplement = () => throwTodoError('implement');
const throwTodoDeprecate = () => throwTodoError('deprecate');

/**
 * Configuration for data processing and storage
 */
export const DB_CONFIG = {
  // Dexie insertion: Max rows per IndexedDB transaction
  // (Prevents UI freeze on large inserts; 5000 is safe for browser)
  BULK_INSERT_CHUNK_SIZE: 5000,
};

export const TIMELINE_STATUS = {
  PROCESSING: 'processing',  // Initial state: ZIP being parsed, data being inserted
  READY: 'ready',           // Success: all data loaded and queryable
  ERROR: 'error',           // Failure: parsing or DB error during import
  ARCHIVED: 'archived',     // User manually archived this timeline
};



// formats data to vue's expectation { data: { objects: [...], meta: {...} } }
function createResponse(objects = [], meta = null) {
  const response = { data: { objects } };
  if (meta) response.data.meta = meta;
  return response;
}



async function getIdentifierFieldsFromYaml() {
  try {
    const response = await fetch('/schemas/all_fields.yaml');
    const text = await response.text();
    const doc = yaml.load(text);
    const identifierFields = doc.device_id_fields || [];
    // all_fields.yaml has device_id_fields as a list of strings now
    return Array.isArray(identifierFields) ? identifierFields : [];
  } catch (e) {
    console.error('Error loading identifier fields:', e);
    return [];
  }
}

let identifierFields = [];
let identifierFieldsStr = '';

// Initialize database schema (synchronous - just registers versions)
// Dexie schemas must be registered synchronously
function initDB() {
  db.version(1).stores({
    sketches: '++id, name, description, user_id, label_string, status, created_at, updated_at',
    timelines: '++id, sketch_id, name, user_id, description, status, color, label_string, datasources, deleted, created_at, updated_at',
    events: '++id, sketch_id, timeline_id, document_id, timestamp, message, data_type, tags, labels, attributes, created_at, updated_at',
    event_comments: '++id, event_id, created_at, updated_at',
    stories: '++id, sketch_id, title, content, user_id, labels, created_at, updated_at',
    views: '++id, sketch_id, name, query, filter, dsl, user_id, created_at, updated_at',
    
    graphs: '++id, user_id, sketch_id, name, description, graph_config, graph_elements, graph_thumbnail, num_nodes, num_edges, created_at, updated_at',
    sigma_rules: '++id, sketch_id, rule_uuid, title, description, rule_yaml, user_id, status, created_at, updated_at',
    scenarios: '++id, sketch_id, user_id, name, display_name, description, summary, dfiq_identifier, uuid, spec_json, created_at, updated_at',
    facets: '++id, sketch_id, scenario_id, user_id, name, display_name, description, dfiq_identifier, uuid, spec_json, created_at, updated_at',
    questions: '++id, sketch_id, user_id, scenario_id, facet_id, name, display_name, description, dfiq_identifier, uuid, spec_json, created_at, updated_at',
  });

  db.version(2).stores({
    events: `++id, sketch_id, timeline_id, source_file, source_line, tags, labels, attributes, created_at, updated_at, original_record, category ${identifierFieldsStr ? ', ' + identifierFieldsStr : ''}`,
    states: `++id, sketch_id, timeline_id, source_file, source_line, tags, labels, attributes, created_at, updated_at, original_record, category ${identifierFieldsStr ? ', ' + identifierFieldsStr : ''}`,
    document_metadata: '++id, sketch_id, timeline_id, platform_name, labels, path, document_created_at, document_updated_at, size_bytes, mime_type, source_type, source_config, hash_sha256, created_at, updated_at',

    timelines: '++id, sketch_id, name, platform_name, description, status, color, label_string, datasources, deleted, created_at, updated_at',
    sketches: '++id, name, description, user_id, label_string, status, created_at, updated_at',
    
    event_comments: '++id, event_id, created_at, updated_at',
    stories: '++id, sketch_id, title, content, user_id, labels, created_at, updated_at',
    views: '++id, sketch_id, name, query, filter, dsl, user_id, created_at, updated_at',
  });
}

const db = new Dexie('TimesketchBrowser');
initDB();

// Load identifier fields in background (async, non-blocking)
getIdentifierFieldsFromYaml().then(fields => {
  identifierFields = fields;
  identifierFieldsStr = fields.join(', ');
});


// --- API-mirrored methods ---
const BrowserDB = {
  // Sketch
  async getSketchList(scope, page, perPage, searchQuery) {
    let collection = db.sketches;
    if (searchQuery) {
      collection = collection.filter(sketch =>
        sketch.name && sketch.name.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }
    let sketches = await collection.toArray();
    const totalItems = sketches.length;
    if (typeof page === 'number' && typeof perPage === 'number') {
      const start = (page - 1) * perPage;
      sketches = sketches.slice(start, start + perPage);
    }
    return createResponse(sketches, { total_items: totalItems });
  },
  async getSketch(sketchId) {
    const sketch = await db.sketches.get(sketchId);
    if (sketch) {
      const timelinesResponse = await this.getTimelines(sketchId);
      sketch.timelines = timelinesResponse.data.objects || [];
    }
    return createResponse([sketch]);
  },
  async ensureSketchInitialized(sketchId = 1) {
    /**
     * Ensure database is initialized and sketch exists.
     * On first visit, creates sketch/1 if it doesn't exist.
     * Subsequent visits just return existing sketch.
     * 
     * @returns sketch object or newly created sketch
     */
    try {
      const sketch = await db.sketches.get(sketchId);
      if (sketch) return sketch;
      
      // Sketch doesn't exist - create it
      console.log(`[BrowserDB] Sketch ${sketchId} not found. Creating default sketch...`);
      const now = new Date().toISOString();
      const newSketch = {
        id: sketchId,
        name: 'My Data',
        description: 'Personal forensic timeline',
        user_id: 'local-user',
        label_string: 'default',
        status: 'active',
        created_at: now,
        updated_at: now,
      };
      await db.sketches.add(newSketch);
      return await db.sketches.get(sketchId);
    } catch (error) {
      console.error('[BrowserDB] Error ensuring sketch initialized:', error);
      throw error;
    }
  },
  async getTimelines(sketchId) {
    const timelines = await db.timelines.where('sketch_id').equals(sketchId).toArray();
    return createResponse(timelines);
  },
  async generateTimelineName(sketchId, platformName) {
    try {
      const timelines = await db.timelines
        .where('sketch_id').equals(sketchId)
        .filter(tl => tl.platform_name === platformName)
        .toArray();
      
      if (timelines.length === 0) {
        return platformName;
      }
      
      return `${platformName}-${timelines.length + 1}`;
    } catch (error) {
      console.warn(`Error suggesting timeline name for ${platformName}:`, error);
      return platformName;
    }
  },
  async createSketch(formData) {
    const now = new Date().toISOString();
    const sketch = {
      name: formData.name || '',
      description: formData.description || '',
      user_id: formData.user_id || null,
      label_string: formData.label_string || '',
      status: formData.status || 'active',
      created_at: now,
      updated_at: now,
    };
    const id = await db.sketches.add(sketch);
    const newSketch = await db.sketches.get(id);
    return createResponse([newSketch]);
  },
  async deleteSketch(sketchId) {
    await db.stories.where('sketch_id').equals(sketchId).delete();
    const timelines = await db.timelines.where('sketch_id').equals(sketchId).toArray();
    for (const timeline of timelines) {
      await this.deleteSketchTimeline(sketchId, timeline.id);
    }
    await db.events.where('sketch_id').equals(sketchId).and(ev => !ev.timeline_id).delete();
    await db.sketches.delete(sketchId);
    return createResponse([]);
  },

  async archiveSketch(sketchId) {
    throwTodoDeprecate();
  },
  async unArchiveSketch(sketchId) {
    throwTodoDeprecate();
  },
  async exportSketch(sketchId) {
    throwTodoImplement();
  },
  async getSketchAttributes(sketchId) {
    throwTodoImplement();
  },
  async addSketchAttribute(sketchId, name, value, ontology) {
    throwTodoImplement();
  },
  
  async getSketchTimeline(sketchId, timelineId) {
    // Return a single timeline for a sketch by timelineId
    const timeline = await db.timelines.get(timelineId);
    if (timeline && timeline.sketch_id === sketchId) {
      return createResponse([timeline]);
    }
    return createResponse([]);
  },

  async getSketchTimelineAnalysis(sketchId, timelineId) {
    throwTodoImplement();
  },
  async getTimelineFields(sketchId, timelineId) {
    throwTodoImplement();
  },
  
  async saveSketchTimeline(sketchId, timelineId, name, description, color, status) {
    // Update timeline metadata
    const now = new Date().toISOString();
    const updateObj = { updated_at: now };
    if (name !== undefined) updateObj.name = name;
    if (description !== undefined) updateObj.description = description;
    if (color !== undefined) updateObj.color = color;
    if (status !== undefined) updateObj.status = status;

    await db.timelines.update(timelineId, updateObj);
    const updated_timeline = await db.timelines.get(timelineId);
    return createResponse([updated_timeline]);
  },
  async saveSketchSummary(sketchId, name, description) {
    // Update sketch metadata (name, description)
    const now = new Date().toISOString();
    await db.sketches.update(sketchId, {
      name,
      description,
      updated_at: now,
    });
    const updated_sketch = await db.sketches.get(sketchId);
    return createResponse([updated_sketch]);
  },
  async deleteSketchTimeline(sketchId, timelineId) {
    // Cascade delete events and their comments for this timeline
    const events = await db.events.where('timeline_id').equals(timelineId).toArray();
    for (const event of events) {
      await db.event_comments.where('event_id').equals(event.id).delete();
      await this._deleteEvent(sketchId, timelineId, event.id);
    }
    await db.timelines.delete(timelineId);
    return createResponse([]);
  },

  // ----------------------------------------------------------
  // Events
  async createEvent(sketchId, datetime, message, timestampDesc, attributes, config) {
    // Create a new event (manual event creation)
    const now = new Date().toISOString();
    const event = {
      sketch_id: sketchId,
      timeline_id: null, // Manual events may not have a timeline
      document_id: crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2),
      timestamp: datetime ? new Date(datetime).getTime() * 1000 : Date.now() * 1000,
      message: message || 'No message string',
      data_type: attributes && attributes.data_type ? attributes.data_type : 'manual',
      tags: attributes && attributes.tag ? attributes.tag : [],
      labels: [],
      attributes: attributes || {},
      created_at: now,
      updated_at: now,
    };
    const id = await db.events.add(event);
    const newEvent = await db.events.get(id);
    return createResponse([newEvent]);
  },

  async createState(sketchId, datetime, message, timestampDesc, attributes, config) {
    // Create a new state (manual state creation)
    const now = new Date().toISOString();
    const state = {
      sketch_id: sketchId,
      timeline_id: null,
      timestamp: datetime ? new Date(datetime).getTime() * 1000 : Date.now() * 1000,
      message: message || 'No message string',
      data_type: attributes && attributes.data_type ? attributes.data_type : 'manual',
      tags: attributes && attributes.tag ? attributes.tag : [],
      labels: [],
      attributes: attributes || {},
      created_at: now,
      updated_at: now,
    };
    const id = await db.states.add(state);
    const newState = await db.states.get(id);
    return createResponse([newState]);
  },

  async getEvent(sketchId, searchindexId, eventId, includeProcessingTimelines) {
    // Find event by ID and fetch associated comments
    const event = await db.events.get(eventId);
    if (!event) return createResponse([]);
    
    // Fetch comments for this event
    const comments = await db.event_comments.where('event_id').equals(eventId).toArray();
    
    // Prepare comment objects with user info for display
    const preparedComments = comments.map(c => ({
      id: c.id,
      user: { username: 'local-user' },  // Browser version has single user
      comment: c.content,
      created_at: c.created_at,
      updated_at: c.updated_at,
      editable: false
    }));
    
    return createResponse([event], { comments: preparedComments });
  },

  async countSketchEvents(sketchId) {
    // Just call countEvents with no timelineId to count all
    const count = await this.countEvents(sketchId);
    return createResponse([], { count });
  },

  async countSketchStates(sketchId) {
    // Just call countStates with no timelineId to count all
    const count = await this.countStates(sketchId);
    return createResponse([], { count });
  },

  async countEvents(sketchId, timelineId = null) {
    let query = db.events.where('sketch_id').equals(sketchId);
    if (timelineId) {
      query = query.filter(ev => ev.timeline_id === timelineId);
    }
    const count = await query.count();
    return count;
  },

  async countStates(sketchId, timelineId = null) {
    let query = db.states.where('sketch_id').equals(sketchId);
    if (timelineId) {
      query = query.filter(st => st.timeline_id === timelineId);
    }
    const count = await query.count();
    return count;
  },

  async bulkInsert(sketchId, timelineId, events = [], states = []) {
    /**
     * Bulk insert events and states in a single transaction.
     * 
     * If ANY operation fails (events or states), the ENTIRE transaction rolls back.
     * This prevents orphaned data where events exist but states don't, or vice versa.
     * 
     * Inserts are chunked to prevent UI freeze, but all chunks are within one transaction.
     */
    const now = new Date().toISOString();
    const chunkSize = DB_CONFIG.BULK_INSERT_CHUNK_SIZE;
    
    const prepareRow = (row) => ({
      ...row,
      sketch_id: sketchId,
      timeline_id: timelineId,
      created_at: row.created_at || now,
      updated_at: now,
      tags: row.tags || [],
      labels: row.labels || [],
      attributes: row.attributes || {}
    });

    // Single transaction wrapping both events and states
    return db.transaction('rw', db.events, db.states, async () => {
      // Chunk and insert events
      if (events.length > 0) {
        const preparedEvents = events.map(prepareRow);
        
        for (let i = 0; i < preparedEvents.length; i += chunkSize) {
          const batch = preparedEvents.slice(i, i + chunkSize);
          await db.events.bulkAdd(batch);
          const batchNum = Math.ceil((i + chunkSize) / chunkSize);
          const totalBatches = Math.ceil(preparedEvents.length / chunkSize);
          console.log(`[BulkInsert] Events batch ${batchNum}/${totalBatches} inserted (${batch.length} rows)`);
        }
      }
      
      // Chunk and insert states (within same transaction)
      if (states.length > 0) {
        const preparedStates = states.map(prepareRow);
        
        for (let i = 0; i < preparedStates.length; i += chunkSize) {
          const batch = preparedStates.slice(i, i + chunkSize);
          await db.states.bulkAdd(batch);
          const batchNum = Math.ceil((i + chunkSize) / chunkSize);
          const totalBatches = Math.ceil(preparedStates.length / chunkSize);
          console.log(`[BulkInsert] States batch ${batchNum}/${totalBatches} inserted (${batch.length} rows)`);
        }
      }
    });
  },


  async addCommentEvent(eventId, content) {
    // Add a comment to an event
    const now = new Date().toISOString();
    await db.event_comments.add({
      event_id: eventId,
      content,
      created_at: now,
      updated_at: now
    });
    return createResponse([]);
  },

  // Legacy method for backward compatibility
  async saveComment(eventId, content) {
    return this.addCommentEvent(eventId, content);
  },

  // Legacy method for backward compatibility
  async saveAnnotation(
    objectType, /* e.g., 'event' - for comments */
    objectIds,  /* arr of event_ids */
    annotationType, /* 'comment' - currently only type supported */
    content) {
    if (objectType !== 'event' || annotationType !== 'comment') {
      throw new Error('Only event comments are supported');
    }
    for (const eventId of objectIds) {
      await this.addCommentEvent(eventId, content);
    }
    return createResponse([]);
  },

  async tagEvent(eventIds, tagsToAdd /* array of strings */) {
    const now = new Date().toISOString();
    for (const eventId of eventIds) {
      const event = await db.events.get(eventId);
      if (event) {
        const updatedTags = Array.from(new Set([...(event.tags || []), ...tagsToAdd]));
        await db.events.update(eventId, {
          tags: updatedTags,
          updated_at: now
        });
      }
    }
    return createResponse([]);
  },

  async untagEvent(eventIds, tagsToRemove /* array of strings */) {
    const now = new Date().toISOString();
    for (const eventId of eventIds) {
      const event = await db.events.get(eventId);
      if (event) {
        const updatedTags = (event.tags || []).filter(tag => !tagsToRemove.includes(tag));
        await db.events.update(eventId, {
          tags: updatedTags,
          updated_at: now
        });
      }
    }
    return createResponse([]);
  },

  async tagState(stateIds, tagsToAdd /* array of strings */) {
    const now = new Date().toISOString();
    for (const stateId of stateIds) {
      const state = await db.states.get(stateId);
      if (state) {
        const updatedTags = Array.from(new Set([...(state.tags || []), ...tagsToAdd]));
        await db.states.update(stateId, {
          tags: updatedTags,
          updated_at: now
        });
      }
    }
    return createResponse([]);
  },

  async untagState(stateIds, tagsToRemove /* array of strings */) {
    const now = new Date().toISOString();
    for (const stateId of stateIds) {
      const state = await db.states.get(stateId);
      if (state) {
        const updatedTags = (state.tags || []).filter(tag => !tagsToRemove.includes(tag));
        await db.states.update(stateId, {
          tags: updatedTags,
          updated_at: now
        });
      }
    }
    return createResponse([]);
  },

  // Legacy generic methods - use event/state-specific versions instead
  async tagObjects(objectType, objectIds, tagsToAdd /* array of strings */) {
    if (objectType === 'event') {
      return this.tagEvent(objectIds, tagsToAdd);
    } else if (objectType === 'state') {
      return this.tagState(objectIds, tagsToAdd);
    }
    return createResponse([]);
  },

  async untagObjects(objectType, objectIds, tagsToRemove /* array of strings */) {
    if (objectType === 'event') {
      return this.untagEvent(objectIds, tagsToRemove);
    } else if (objectType === 'state') {
      return this.untagState(objectIds, tagsToRemove);
    }
    return createResponse([]);
  },

  async addLabelEvent(eventIds, labelsToAdd /* array of strings */) {
    const now = new Date().toISOString();
    for (const eventId of eventIds) {
      const event = await db.events.get(eventId);
      if (event) {
        const updatedLabels = Array.from(new Set([...(event.labels || []), ...labelsToAdd]));
        await db.events.update(eventId, {
          labels: updatedLabels,
          updated_at: now
        });
      }
    }
    return createResponse([]);
  },

  async removeLabelEvent(eventIds, labelsToRemove /* array of strings */) {
    const now = new Date().toISOString();
    for (const eventId of eventIds) {
      const event = await db.events.get(eventId);
      if (event) {
        const updatedLabels = (event.labels || []).filter(label => !labelsToRemove.includes(label));
        await db.events.update(eventId, {
          labels: updatedLabels,
          updated_at: now
        });
      }
    }
    return createResponse([]);
  },

  async addLabelState(stateIds, labelsToAdd /* array of strings */) {
    const now = new Date().toISOString();
    for (const stateId of stateIds) {
      const state = await db.states.get(stateId);
      if (state) {
        const updatedLabels = Array.from(new Set([...(state.labels || []), ...labelsToAdd]));
        await db.states.update(stateId, {
          labels: updatedLabels,
          updated_at: now
        });
      }
    }
    return createResponse([]);
  },

  async removeLabelState(stateIds, labelsToRemove /* array of strings */) {
    const now = new Date().toISOString();
    for (const stateId of stateIds) {
      const state = await db.states.get(stateId);
      if (state) {
        const updatedLabels = (state.labels || []).filter(label => !labelsToRemove.includes(label));
        await db.states.update(stateId, {
          labels: updatedLabels,
          updated_at: now
        });
      }
    }
    return createResponse([]);
  },

  // Legacy generic methods - use event/state-specific versions instead
  async addLabels(objectType, objectIds, labelsToAdd /* array of strings */) {
    if (objectType === 'event') {
      return this.addLabelEvent(objectIds, labelsToAdd);
    } else if (objectType === 'state') {
      return this.addLabelState(objectIds, labelsToAdd);
    }
    return createResponse([]);
  },

  async removeLabels(objectType, objectIds, labelsToRemove /* array of strings */) {
    if (objectType === 'event') {
      return this.removeLabelEvent(objectIds, labelsToRemove);
    } else if (objectType === 'state') {
      return this.removeLabelState(objectIds, labelsToRemove);
    }
    return createResponse([]);
  },

  async updateCommentEvent(commentId, content) {
    // Update comment content
    const now = new Date().toISOString();
    await db.event_comments.update(commentId, { content, updated_at: now });
    const updated = await db.event_comments.get(commentId);
    return createResponse([updated]);
  },

  // Legacy method for backward compatibility
  async updateComment(commentId, content) {
    return this.updateCommentEvent(commentId, content);
  },

  // Legacy method for backward compatibility
  async updateAnnotation(annotationType, content, annotationIds) {
    if (annotationType !== 'comment') {
      throw new Error('Only event comments are supported');
    }
    const results = [];
    for (const commentId of annotationIds) {
      const response = await this.updateCommentEvent(commentId, content);
      if (response.data.objects[0]) results.push(response.data.objects[0]);
    }
    return createResponse(results);
  },

  async deleteCommentEvent(commentId) {
    // Delete a comment
    await db.event_comments.delete(commentId);
    return createResponse([]);
  },

  // Legacy method for backward compatibility
  async deleteComment(commentId) {
    return this.deleteCommentEvent(commentId);
  },

  // Legacy method for backward compatibility
  async deleteEventAnnotation(annotationId) {
    return this.deleteCommentEvent(annotationId);
  },
  
  async _deleteEvent(eventId) {
    await db.event_comments.where('event_id').equals(eventId).delete();
    await db.events.delete(eventId);
  },

  async _deleteState(stateId) {
    // States don't have comments in this implementation
    await db.states.delete(stateId);
  },
  
  // ----------------------------------------------------------
  // Stories
  async getStoryList(sketchId) {
    const stories = await db.stories.where('sketch_id').equals(sketchId).toArray();
    return createResponse(stories);
  },
  async getStory(sketchId, storyId) {
    const story = await db.stories.get(storyId);
    return createResponse([story]);
  },
  async createStory(title, content, sketchId) {
    const now = new Date().toISOString();
    const story = {
      sketch_id: sketchId,
      title,
      content,
      created_at: now,
      updated_at: now,
    };
    const id = await db.stories.add(story);
    const newStory = await db.stories.get(id);
    return createResponse([newStory]);
  },
  async updateStory(title, content, sketchId, storyId) {
    const now = new Date().toISOString();
    await db.stories.update(storyId, { title, content, updated_at: now });
    const updated = await db.stories.get(storyId);
    return createResponse([updated]);
  },
  async deleteStory(sketchId, storyId) {
    await db.stories.delete(storyId);
    return createResponse([]);
  },

  // ----------------------------------------------------------
  // Views (Saved searches)
  async getView(sketchId, viewId) {
    // Return a single view by id and sketchId
    const view = await db.views.get(viewId);
    if (view && view.sketch_id === sketchId) {
      return createResponse([view]);
    }
    return createResponse([]);
  },

  async createView(sketchId, viewName, queryString, queryFilter) {
    const now = new Date().toISOString();
    const view = {
      sketch_id: sketchId,
      name: viewName,
      query: queryString,
      filter: queryFilter,
      dsl: '',
      user: null, // Set if you have user info
      created_at: now,
      updated_at: now,
    };
    const id = await db.views.add(view);
    const newView = await db.views.get(id);
    return createResponse([newView]);
  },
  async updateView(sketchId, viewId, queryString, queryFilter) {
    const now = new Date().toISOString();
    await db.views.update(viewId, {
      query: queryString,
      filter: queryFilter,
      updated_at: now,
    });
    const updated = await db.views.get(viewId);
    return createResponse([updated]);
  },
  async deleteView(sketchId, viewId) {
    await db.views.delete(viewId);
    return createResponse([]);
  },

  // ----------------------------------------------------------
  // Search templates
  async getSearchTemplates() {
    throwTodoImplement();
  },
  async parseSearchTemplate(searchTemplateId, formData) {
    throwTodoImplement();
  },
  
  // ----------------------------------------------------------
  // Search
  /**
   * Get events from database with optional filtering
   * @param {number} sketchId - Sketch ID
   * @param {object} options - Query options
   * @param {array} options.timelineIds - Filter by timeline IDs (null/undefined = all)
   * @param {string} options.query - Search query string (null = all)
   * @param {string} options.order - 'asc' or 'desc' (default: 'desc')
   * @param {number} options.limit - Max results to return
   * @param {number} options.offset - Offset for pagination
   * @returns {Promise<array>} Array of events
   */
  async getEvents(sketchId, options = {}) {
    const { timelineIds, query, order = 'desc', limit, offset = 0 } = options;
    
    // Start with sketch filter
    let eventsQuery = db.events.where('sketch_id').equals(sketchId);
    
    // Filter by timelines if specified
    if (timelineIds && Array.isArray(timelineIds) && timelineIds.length > 0) {
      eventsQuery = eventsQuery.filter(ev => timelineIds.includes(ev.timeline_id));
    }
    
    // Filter by query string if provided
    if (query) {
      const queryLower = query.toLowerCase();
      eventsQuery = eventsQuery.filter(ev => 
        ev.message && ev.message.toLowerCase().includes(queryLower)
      );
    }
    
    // Get results
    let results = await eventsQuery.toArray();
    
    // Sort by primary_timestamp (descending = most recent first by default)
    results.sort((a, b) => {
      const aTime = a.primary_timestamp || a.timestamp || 0;
      const bTime = b.primary_timestamp || b.timestamp || 0;
      return order === 'desc' ? bTime - aTime : aTime - bTime;
    });
    
    // Apply limit and offset
    if (limit !== undefined) {
      results = results.slice(offset, offset + limit);
    }
    
    return results;
  },

  /**
   * Legacy search method for backward compatibility
   * Returns Timesketch-style response format
   */
  async search(sketchId, formData) {
    // Extract parameters from formData
    const query = (formData && formData.query) || null;
    const order = (formData && formData.filter && formData.filter.order) || 'desc';
    const size = (formData && formData.filter && formData.filter.size) || 40;
    const from = (formData && formData.filter && formData.filter.from) || 0;
    
    // Handle timeline filtering
    let timelineIds = formData && formData.filter && formData.filter.indices;
    if (!timelineIds || timelineIds === '_all' || 
        (Array.isArray(timelineIds) && (timelineIds.length === 0 || timelineIds.includes('_all')))) {
      timelineIds = null; // All timelines
    }
    
    // Build count_per_timeline by fetching ALL matching results to get accurate counts
    // This ensures counts are accurate when filtering by query
    const allMatching = await this.getEvents(sketchId, {
      timelineIds,
      query,
      order
    });
    
    // Count by timeline from all matching results
    const countPerTimeline = {};
    allMatching.forEach(ev => {
      const tlId = ev.timeline_id;
      countPerTimeline[tlId] = (countPerTimeline[tlId] || 0) + 1;
    });
    
    const totalCount = allMatching.length;
    
    // Get the specific page of results
    const results = await this.getEvents(sketchId, {
      timelineIds,
      query,
      order,
      limit: size + 1, // +1 to check hasNextPage
      offset: from
    });
    
    // Check if there's a next page
    const hasNextPage = results.length > size;
    const pagedEvents = results.slice(0, size);
    
    // Wrap in Timesketch-style format
    const objects = pagedEvents.map(ev => ({ _id: ev.id, _source: ev }));
    
    const meta = {
      num_events: pagedEvents.length,
      num_states: 0,
      has_next_page: hasNextPage,
      query_time_ms: 0,
      count_per_timeline: countPerTimeline,
      total_count: totalCount,
      summary: '',
    };
    
    return createResponse(objects, meta);
  },
  /**
   * Get states from database with optional filtering
   * @param {number} sketchId - Sketch ID
   * @param {object} options - Query options (same as getEvents)
   * @returns {Promise<array>} Array of states
   */
  async getStates(sketchId, options = {}) {
    const { timelineIds, query, order = 'desc', limit, offset = 0 } = options;
    
    let statesQuery = db.states.where('sketch_id').equals(sketchId);
    
    if (timelineIds && Array.isArray(timelineIds) && timelineIds.length > 0) {
      statesQuery = statesQuery.filter(st => timelineIds.includes(st.timeline_id));
    }
    
    if (query) {
      const queryLower = query.toLowerCase();
      statesQuery = statesQuery.filter(st => 
        st.message && st.message.toLowerCase().includes(queryLower)
      );
    }
    
    let results = await statesQuery.toArray();
    
    results.sort((a, b) => {
      const diff = (a.timestamp || 0) - (b.timestamp || 0);
      return order === 'asc' ? diff : -diff;
    });
    
    if (limit !== undefined) {
      results = results.slice(offset, offset + limit);
    }
    
    return results;
  },

  async exportSearchResult(sketchId, formData) {},
  async getSearchHistory(sketchId, limit = null, question = null) {},
  async getSearchHistoryTree(sketchId) {},
  
  // ----------------------------------------------------------
  // Aggregations
  async getAggregations(sketchId) {
    throwTodoImplement();
  },
  async getAggregationById(sketchId, aggregationId) {
    throwTodoImplement();
  },
  async deleteAggregationById(sketchId, aggregationId) {
    throwTodoImplement();
  },
  async getAggregationGroups(sketchId) {
    throwTodoImplement();
  },
  async runAggregator(sketchId, formData) {
    throwTodoImplement();
  },
  async runAggregatorGroup(sketchId, groupId) {
    throwTodoImplement();
  },
  async saveAggregation(sketchId, aggregation, name, formData) {
    throwTodoImplement();
  },
  
    // ----------------------------------------------------------
  // Sharing and authorization (no-ops or local-only)
  async getUsers() {
    throwTodoDeprecate();
  },
  async getGroups() {
    throwTodoDeprecate();
  },
  async grantSketchAccess(sketchId, usersToAdd, groupsToAdd) {
    throwTodoDeprecate();
  },
  async revokeSketchAccess(sketchId, usersToRemove, groupsToRemove) {
    throwTodoDeprecate();
  },
  async setSketchPublicAccess(sketchId, isPublic) {
    throwTodoDeprecate();
  },
  
  // ----------------------------------------------------------
  // Analyzers (local-only or no-op)
  async getAnalyzers(sketchId) {
    return createResponse([]);
  },
  async runAnalyzers(sketchId, timelineIds, analyzers, forceRun = false) {
    return createResponse([]);
  },
  async getAnalyzerSession(sketchId, sessionId) {
    return createResponse([]);
  },
  async getActiveAnalyzerSessions(sketchId) {
    return createResponse([]);
  },
  
  // ----------------------------------------------------------
  // Graphs
  async generateGraphFromPlugin(sketchId, graphPlugin, currentIndices, timelineIds, refresh) {
    throwTodoImplement();
  },
  async getGraphPluginList() {
    throwTodoImplement();
  },
  async saveGraph(sketchId, name, elements) {
    throwTodoImplement();
  },
  async getSavedGraphList(sketchId) {
    throwTodoImplement();
  },
  async getSavedGraph(sketchId, graphId) {
    throwTodoImplement();
  },
  
  // ----------------------------------------------------------  
  // Sigma
  async getSigmaRuleList() {
    throwTodoImplement();
  },
  async getSigmaRuleResource(ruleUuid) {
    throwTodoImplement();
  },
  async getSigmaRuleByText(ruleYaml) {
    throwTodoImplement();
  },
  async deleteSigmaRule(ruleUuid) {
    throwTodoImplement();
  },
  async createSigmaRule(ruleYaml) {
    throwTodoImplement();
  },
  async updateSigmaRule(id, ruleYaml) {
    throwTodoImplement();
  },
  
  // ----------------------------------------------------------  
  // Scenarios
  async getScenarioTemplates() {},
  async getSketchScenarios(sketchId, status = null) {},
  async addScenario(sketchId, scenarioId, displayName) {},
  async renameScenario(sketchId, scenarioId, scenarioName) {},
  async setScenarioStatus(sketchId, scenarioId, status) {},
  async getFacets(sketchId, scenarioId) {},
  async getQuestionTemplates() {},
  async getOrphanQuestions(sketchId) {},
  async getScenarioQuestions(sketchId, scenarioId) {},
  async getFacetQuestions(sketchId, scenarioId, facetId) {},
  async getQuestion(sketchId, questionId) {},
  async createQuestion(sketchId, scenarioId, facetId, questionText, templateId) {},
  async createQuestionConclusion(sketchId, questionId, conclusionText) {},
  async editQuestionConclusion(sketchId, questionId, conclusionId, conclusionText) {},
  async deleteQuestionConclusion(sketchId, questionId, conclusionId) {},
  
  // ----------------------------------------------------------  
  // Misc resources
  async getTagMetadata() {
    // Return tag metadata from config file
    // Tags are manually added by users - this metadata just defines styling/display
    return createResponse([tagMetadata])
  },
  async uploadTimeline(formData, config) {},
  async getSessions(sketchId, timelineIndex) {},
  async getLoggedInUser() {},
  async getContextLinkConfig() {},
  async getUnfurlGraph(url) {},
  async getSystemSettings() {},
  async getUserSettings() {},
  async saveUserSettings(settings) {},
  async llmRequest(sketchId, featureName, formData) {},




  // ----------------------------------------------------------
  // Document Metadata
  async createDocumentMetadata({
    sketch_id,
    timeline_id,
    platform_name,
    path = '',
    file_name = '',
    size_bytes = 0,
    mime_type = '',
    source_type = 'zip_upload',
    source_config = {},
    hash_sha256 = '',
    labels = [],
    parse_status = 'pending',
    parse_error_message = null,
    rows_parsed = 0,
  }) {
    const now = new Date().toISOString();
    const metadata = {
      sketch_id,
      timeline_id,
      platform_name,
      path,
      file_name,
      size_bytes,
      mime_type,
      source_type,
      source_config: source_config || {},
      hash_sha256,
      labels: labels || [],
      document_created_at: now,
      document_updated_at: now,
      created_at: now,
      updated_at: now,
    };
    
    // Store parse status in source_config for easier querying
    if (parse_status || parse_error_message || rows_parsed > 0) {
      metadata.source_config = {
        ...metadata.source_config,
        parse_status,
        parse_error_message,
        rows_parsed,
      };
    }
    
    const id = await db.document_metadata.add(metadata);
    const newMetadata = await db.document_metadata.get(id);
    return createResponse([newMetadata]);
  },

  async getDocumentMetadataByTimeline(timelineId) {
    const metadata = await db.document_metadata.where('timeline_id').equals(timelineId).toArray();
    return createResponse(metadata);
  },

  async getDocumentMetadataByHash(sketchId, hash) {
    const metadata = await db.document_metadata
      .where('sketch_id').equals(sketchId)
      .filter(m => m.hash_sha256 === hash)
      .toArray();
    return createResponse(metadata);
  },

  async updateDocumentMetadata(metadataId, updates) {
    const now = new Date().toISOString();
    const updateObj = { ...updates, updated_at: now };
    await db.document_metadata.update(metadataId, updateObj);
    const updated = await db.document_metadata.get(metadataId);
    return createResponse([updated]);
  },

  // ----------------------------------------------------------
  // Timeline Custom 
  async createTimeline({
    id = undefined,
    sketch_id,
    name,
    platform_name,
    description = '',
    status = '',
    color = '',
    label_string = '',
    datasources = null,
    deleted = false,
  }) {
    const now = new Date().toISOString();
    const timeline = {
      id,
      sketch_id,
      name,
      platform_name,
      description,
      status,
      color,
      label_string,
      datasources,
      deleted,
      created_at: now,
      updated_at: now,
     
    };
    // Remove undefined fields (Dexie will auto-increment id if undefined)
    Object.keys(timeline).forEach(key => timeline[key] === undefined && delete timeline[key]);
    const timelineId = await db.timelines.add(timeline);
    const newTimeline = await db.timelines.get(timelineId);
    return createResponse([newTimeline]);
  },

  // ----------------------------------------------------------
  async wipeAllData() {
    /**
     * Nuclear wipe: Delete the entire IndexedDB database.
     * No trace remains that this tool was ever accessed.
     * Database will be reinitialized on next access.
     */
    try {
      // Close all connections to the database
      await db.close();
      // Delete the entire database
      await db.delete();
      console.log('[BrowserDB] Entire IndexedDB database deleted - no trace remains');
      return { success: true, message: 'All data permanently deleted' };
    } catch (error) {
      console.error('[BrowserDB] Error wiping database:', error);
      throw error;
    }
  },
}

export default BrowserDB;
export { db };

