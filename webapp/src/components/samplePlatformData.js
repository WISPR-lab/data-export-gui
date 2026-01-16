// Direct Dexie insert for debug/dev
import { db } from '../database.js';

// Dexie instance is available as BrowserDB.db
export async function pushSampleEventsToDB() {
  // Always create a new timeline and link events to it
  const timelineName = samplePlatformData.name + ' ' + new Date().toISOString();
  const timeline = {
    sketch_id: samplePlatformData.sketch_id,
    name: timelineName,
    platform_name: samplePlatformData.provider,
    description: 'Sample timeline for debug',
    status: 'active',
    color: '#2196f3',
    label_string: '',
    datasources: null,
    deleted: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  let timelineId;
  try {
    timelineId = await db.timelines.add(timeline);
  } catch (e) {
    if (e.name === 'ConstraintError') {
      // Overwrite: clear timelines table and retry
      // eslint-disable-next-line no-console
      console.warn('Timeline ConstraintError: clearing timelines table and retrying.');
      await db.timelines.clear();
      timelineId = await db.timelines.add(timeline);
    } else {
      throw e;
    }
  }
  // Insert events, referencing the new timeline
  try {
    for (const event of samplePlatformData.events) {
      await db.events.add({
        ...event,
        timeline_id: timelineId,
        document_id: event.document_id + '-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8),
      });
    }
  } catch (e) {
    if (e.name === 'ConstraintError') {
      // Overwrite: clear events table and retry
      // eslint-disable-next-line no-console
      console.warn('Event ConstraintError: clearing events table and retrying.');
      await db.events.clear();
      for (const event of samplePlatformData.events) {
        await db.events.add({
          ...event,
          timeline_id: timelineId,
          document_id: event.document_id + '-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8),
        });
      }
    } else {
      throw e;
    }
  }
}

// Test function: fetch all events for the sample sketch_id
export async function testSampleEventsImport() {
  const events = await db.events.where('sketch_id').equals(samplePlatformData.sketch_id).toArray();
  // eslint-disable-next-line no-console
  console.log('Sample events in DB:', events);
  return events;
}
export const samplePlatformData = {
  name: 'Sample Timeline',
  provider: 'SampleProvider',
  context: 'sample.zip',
  total_file_size: 123456,
  sketch_id: 1,
  events: [
    {
      sketch_id: 1,
      timeline_id: 1,
      document_id: 'sample-doc-1',
      document_line: 1,
      timestamp: Date.parse('2025-01-01T12:00:00Z') * 1000, // microseconds
      tags: ['debug'],
      labels: [],
      created_at: '2025-01-01T12:00:00Z',
      updated_at: '2025-01-01T12:00:00Z',
      original_record: '{"event_id":"sample-doc-1","ip":"10.0.0.6","user_agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)","device_model":"MacBookPro15,2","message":"Sample event 1","timestamp":"2025-01-01T12:00:00Z"}',
      parse_category: 'debug',
      ip: '10.0.0.6',
      user_agent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
      device_model: 'MacBookPro15,2',
      session_id: 'session-abc-123',
    },
    {
      sketch_id: 1,
      timeline_id: 1,
      document_id: 'sample-doc-2',
      document_line: 2,
      timestamp: Date.parse('2025-01-02T13:00:00Z') * 1000, // microseconds
      tags: ['debug'],
      labels: [],
      created_at: '2025-01-02T13:00:00Z',
      updated_at: '2025-01-02T13:00:00Z',
      original_record: '{"event_id":"sample-doc-2","ip":"10.0.0.5","user_agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)","device_model":"iPhone14,2","message":"Sample event 2","timestamp":"2025-01-02T13:00:00Z"}',
      parse_category: 'debug',
      ip: '10.0.0.5',
      user_agent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
      device_model: 'iPhone14,2',
      session_id: 'session-def-456',
    },
  ],
}
