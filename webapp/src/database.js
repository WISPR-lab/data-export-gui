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
    annotations: '++id, event_id, type, content, user_id, created_at, updated_at',
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
    
    annotations: '++id, object_type, object_id, type, content, created_at, updated_at',
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
    return createResponse([sketch]);
  },
  async getTimelines(sketchId) {
    const timelines = await db.timelines.where('sketch_id').equals(sketchId).toArray();
    return createResponse(timelines);
  },
  async getNextTimelineNameForPlatform(sketchId, platformName) {
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
    // Cascade delete events and their annotations for this timeline
    const events = await db.events.where('timeline_id').equals(timelineId).toArray();
    for (const event of events) {
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

  async getEvent(sketchId, eventId, includeProcessingTimelines) {
    // Find event by document_id and searchindex_name
    const event = await db.events.where({
      sketch_id: sketchId,
      document_id: eventId
    }).first();
    if (!event) return createResponse([]);
    return createResponse([event]);
  },

  async countSketchEvents(sketchId) {
    const count = await db.events.where('sketch_id').equals(sketchId).count();
    return createResponse([], { count });
  },

  async countSketchStates(sketchId) {
    const count = await db.states.where('sketch_id').equals(sketchId).count();
    return createResponse([], { count });
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


  async saveAnnotation(
    objectType, /* e.g., 'event', 'state', 'document' */
    objectIds,  /* arr of event_id, state_id, document_id */
    annotationType, /* 'comment', 'label', 'tag' */
    content) {
    const now = new Date().toISOString();
    const annotation = {
      object_type: objectType,
      object_ids: objectIds,
      type: annotationType,
      content,
      created_at: now,
      updated_at: now
    };
    for (const objectId of objectIds) {
      const annCopy = { ...annotation, object_id: objectId };
      await db.annotations.add(annCopy);
    }
    return createResponse([]);
  },

  async tagObjects(objectType, objectIds, tagsToAdd /* array of strings */) {
    const now = new Date().toISOString();
    let table = null;
    if (objectType === 'event') {
      table = db.events;
    } else if (objectType === 'state') {
      table = db.states;
    }
    if (!table) return createResponse([]);
    for (const objectId of objectIds) {
      const obj = await table.get(objectId);
      if (obj) {
        const updatedTags = Array.from(new Set([...(obj.tags || []), ...tagsToAdd]));
        await table.update(objectId, {
          tags: updatedTags,
          updated_at: now
        });
      }
    }
    return createResponse([]);
  },

  async untagObjects(objectType, objectIds, tagsToRemove /* array of strings */) {
    const now = new Date().toISOString();
    let table = null;
    if (objectType === 'event') {
      table = db.events;
    } else if (objectType === 'state') {
      table = db.states;
    }
    if (!table) return createResponse([]);
    for (const objectId of objectIds) {
      const obj = await table.get(objectId);
      if (obj) {
        const updatedTags = (obj.tags || []).filter(tag => !tagsToRemove.includes(tag));
        await table.update(objectId, {
          tags: updatedTags,
          updated_at: now
        });
      }
    }
    return createResponse([]);
  },

  async updateAnnotation(annotationType, content, annotationIds) {
    const now = new Date().toISOString();
    const results = [];
    for (const annotationId of annotationIds) {
      await db.annotations.update(annotationId, { content, updated_at: now });
      const updated = await db.annotations.get(annotationId);
      if (updated) results.push(updated);
    }
    return createResponse(results);
  },

  async deleteEventAnnotation(annotationId) {
    await db.annotations.delete(annotationId);
    return createResponse([]);
  },
  
  async _deleteEvent(eventId) {
    await db.annotations.where('object_id').equals(eventId).and(ann => ann.object_type === 'event').delete();
    await db.events.delete(eventId);
  },

  async _deleteState(stateId) {
    await db.annotations.where('object_id').equals(stateId).and(ann => ann.object_type === 'state').delete();
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
  async search(sketchId, formData) {
    let eventsQuery = db.events.where('sketch_id').equals(sketchId);
    let indices = undefined;
    if (formData && formData.filter && formData.filter.indices !== undefined) {
      indices = formData.filter.indices;
    }
    let filterAll = false;
    if (
      indices === undefined ||
      indices === null ||
      (Array.isArray(indices) && (indices.length === 0 || indices.includes('_all')))
      || indices === '_all'
    ) {
      filterAll = true;
    }
    if (!filterAll && Array.isArray(indices)) {
      eventsQuery = eventsQuery.filter(ev => indices.includes(ev.timeline_id));
    }
    // Basic pagination
    let from = 0;
    let size = 40;
    if (formData && formData.filter) {
      from = formData.filter.from || 0;
      size = formData.filter.size || 40;
    }
    let allEvents = await eventsQuery.toArray();
    // Sort by timestamp desc by default
    allEvents.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));
    // Paginate
    const pagedEvents = allEvents.slice(from, from + size);
    // Wrap in Timesketch-style _source
    const objects = pagedEvents.map(ev => ({ _id: ev.document_id, _source: ev }));
    // Meta info
    const meta = {
      es_total_count: allEvents.length,
      es_total_count_complete: allEvents.length,
      es_time: 0,
      count_per_timeline: {},
      count_per_index: {},
      summary: '',
    };
    return createResponse(objects, meta);
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
     * Schema will be recreated automatically on next app load.
     */
    try {
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

