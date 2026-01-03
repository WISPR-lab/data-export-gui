// database.js
// IndexedDB wrapper for Timesketch browser-based storage using Dexie.js

import Dexie from 'dexie';
import yaml from 'js-yaml';
import { readFileSync } from 'fs';
import path from 'path';
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


// formats data to vue's expectation { data: { objects: [...], meta: {...} } }
function createResponse(objects = [], meta = null) {
  const response = { data: { objects } };
  if (meta) response.data.meta = meta;
  return response;
}



function getIdentifierFieldsFromYaml() {
  try {
    const schemaPath = path.resolve(__dirname, '../schemas/schema_validation.yaml');
    const fileContents = readFileSync(schemaPath, 'utf8');
    const doc = yaml.load(fileContents);
    const identifierFields = doc.identifier_fields;
    const required = identifierFields.required || {};
    const optional = identifierFields.optional || {};
    const allFields = new Set([
      ...Object.keys(required),
      ...Object.keys(optional)
    ]);
    return Array.from(allFields);
  } catch (e) {
    return [];
  }
}

const identifierFields = getIdentifierFieldsFromYaml();
const identifierFieldsStr = identifierFields.join(', ');

const db = new Dexie('TimesketchBrowser');

// timeline = platform
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
  events: `++id, sketch_id, timeline_id, document_id, document_line, timestamp, tags, labels, attributes, created_at, updated_at, raw_str, parse_category${identifierFieldsStr ? ', ' + identifierFieldsStr : ''}`,
  states: `++id, sketch_id, timeline_id, document_id, document_line, tags, labels, attributes, created_at, updated_at, raw_str, parse_category, first_timestamp, last_timestamp${identifierFieldsStr ? ', ' + identifierFieldsStr : ''}`,
  document_metadata: '++id, sketch_id, timeline_id, platform_name, labels, path, document_created_at, document_updated_at, size_bytes, mime_type, source_type, source_config, hash_sha256, created_at, updated_at',

  timelines: '++id, sketch_id, name, platform_name, description, status, color, label_string, datasources, deleted, created_at, updated_at',
  sketches: '++id, name, description, user_id, label_string, status, created_at, updated_at',
  
  annotations: '++id, object_type, object_id, type, content, created_at, updated_at',
  stories: '++id, sketch_id, title, content, user_id, labels, created_at, updated_at',
  views: '++id, sketch_id, name, query, filter, dsl, user_id, created_at, updated_at',
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
  
  async saveSketchTimeline(sketchId, timelineId, name, description, color) {
    // Update timeline metadata (name, description, color)
    const now = new Date().toISOString();
    await db.timelines.update(timelineId, {
      name,
      description,
      color,
      updated_at: now,
    });
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
  async search(sketchId, formData) {},
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
}

export default BrowserDB;

