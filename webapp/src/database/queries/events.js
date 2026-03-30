// custom to WISPR-lab/data-export-gui

import { getDB } from '../index.js';
import { buildWhereClause, buildOrderClause, buildPaginationClause } from './eventQueryBuilder.js';

/*
example of 'filter' object
  {
    from: 0,
    terminate_after: 40,
    size: 40,
    order: 'asc',
    uploadIds: [],
    chips: [
      { type: 'tag', value: 'archived', active: true },
      { type: 'term', field: 'user_agent_os_name', value: 'Windows' },
      { type: 'label', value: 'verified' },
      { type: 'datetime:range', value: '2024-01-15T00:00:00Z,2024-01-20T23:59:59Z' }
    ]
  }
*/

export async function searchEvents(queryString = '', filter = {}) {
  const db = await getDB();
  
  const stringCols = ['e.id', 'e.upload_id', 'e.message', 'e.event_category', 'e.event_action', 'e.event_kind', 'ei.device_profiles_data'];
  
  const orderClause = buildOrderClause(filter);
  const { clause: paginationClause, params: paginationParams } = buildPaginationClause(filter);
  const { clause: whereClause, params: whereParams } = buildWhereClause(filter, queryString, stringCols);
  
  const sql = `
    SELECT 
      e.id, 
      e.upload_id, 
      e.timestamp, 
      e.message, 
      e.attributes, 
      e.tags, 
      e.labels,
      e.event_category, 
      e.event_type, 
      e.event_action, 
      e.event_kind,
      f.opfs_filename AS source_file, 
      u.given_name AS timeline_name, 
      u.platform AS platform,
      COALESCE(ei.device_profiles_data, '[]') AS device_profiles_data
    FROM events e
    LEFT JOIN uploaded_files f ON json_extract(e.file_ids, '$[0]') = f.id
    LEFT JOIN uploads u ON e.upload_id = u.id
    LEFT JOIN v_events2profile_indexed ei ON e.id = ei.event_id
    ${whereClause}
    ${orderClause}
    ${paginationClause}
  `;
  
  const allParams = [...whereParams, ...paginationParams];
  
  try {
    const rows = await db.exec(sql, { 
      bind: allParams,
      returnValue: 'resultRows',
      rowMode: 'object'
    });
    console.log(`[searchEvents] Executed SQL: ${sql}`);
    console.log(`[searchEvents] With params: ${JSON.stringify(allParams)}`);
    
    const totalCount = await _getEventsTotalCount(db, whereClause, whereParams);
    const countPerTimeline = await _getEventsCountPerTimeline(db, whereClause, whereParams);
    
    const objects = rows.map(row => _formatEventObject(row));
    
    console.log(`[Search] "${queryString}" --> ${totalCount} results`);
    return {
      objects,
      meta: {
        total_count: totalCount,
        count_per_timeline: countPerTimeline,
      }
    };
  } catch (error) {
    console.error('[searchEvents] ERROR:', error);
    throw error;
  }
}

export async function getEventCount() {
  const db = await getDB();
  const result = await db.exec('SELECT COUNT(*) as count FROM events', {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  const count = (result[0] && result[0].count) || 0;
  console.log('[getEventCount] Total events in DB:', count);
  return count;
}

export async function deleteEvents(eventIds) {
  const db = await getDB();
  
  const ids = Array.isArray(eventIds) ? eventIds : [eventIds];
  if (ids.length === 0) return;
  
  const placeholders = ids.map(() => '?').join(',');
  const sql = `DELETE FROM events WHERE id IN (${placeholders})`;
  
  await db.exec(sql, { bind: ids });
}

// Note: Frontend uses event_action field (from manifest view static fields).
// The event_category field (ECS event.category) is not used in UI filtering.

export async function getEventActions() {
  const db = await getDB();
  const sql = `
    SELECT event_action, COUNT(*) as count 
    FROM events 
    WHERE event_action IS NOT NULL AND event_action != ''
    GROUP BY event_action 
    ORDER BY count DESC
  `;
  
  const rows = await db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  return rows.map(row => ({
    action: row.event_action,
    count: row.count
  }));
}


export async function getEventMessages() {
  const db = await getDB();
  const sql = `
    SELECT message, COUNT(*) as count 
    FROM events 
    WHERE message IS NOT NULL AND message != ''
    GROUP BY message 
    ORDER BY count DESC
  `;
  
  const rows = await db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  if (rows.length === 0) {
      console.warn('[getEventMessages] No event messages found in the database.');
  }

  return rows.map(row => ({
    message: row.message,
    count: row.count
  }));
}

export async function getEventTags() {
  const db = await getDB();
  // Get all events with tags, parse the JSON, and aggregate
  const sql = `
    SELECT tags 
    FROM events 
    WHERE tags IS NOT NULL AND tags != '' AND tags != '[]'
  `;
  
  const rows = await db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  // Aggregate tags from all events
  const tagCounts = {};
  rows.forEach(row => {
    try {
      const tags = JSON.parse(row.tags);
      if (Array.isArray(tags)) {
        tags.forEach(tag => {
          if (tag) {
            tagCounts[tag] = (tagCounts[tag] || 0) + 1;
          }
        });
      }
    } catch (e) {
      console.warn('Failed to parse tags:', row.tags, e);
    }
  });
  
  // Convert to array format with tag/count
  return Object.entries(tagCounts)
    .map(([tag, count]) => ({
      tag,
      count
    }))
    .sort((a, b) => b.count - a.count);
}

export async function getIPAddresses() {
  const db = await getDB();
  const sql = `
    SELECT attributes 
    FROM events 
    WHERE attributes IS NOT NULL AND attributes != ''
  `;
  
  const rows = await db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  const ipCounts = {};
  rows.forEach(row => {
    try {
      const attrs = JSON.parse(row.attributes);
      if (attrs.client_ip) {
        ipCounts[attrs.client_ip] = (ipCounts[attrs.client_ip] || 0) + 1;
      }
    } catch (e) {
      console.warn('Failed to parse attributes for IP extraction:', e);
    }
  });
  
  return Object.entries(ipCounts)
    .map(([ip_address, count]) => ({
      ip_address,
      count
    }))
    .sort((a, b) => b.count - a.count);
}

async function _getEventsTotalCount(db, whereClause, whereParams) {
  const sql = `SELECT COUNT(*) as count FROM events e LEFT JOIN uploads u ON e.upload_id = u.id LEFT JOIN v_events2profile_indexed ei ON e.id = ei.event_id ${whereClause}`;
  const result = await db.exec(sql, {
    bind: whereParams,
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  return (result[0] && result[0].count) || 0;
}

async function _getEventsCountPerTimeline(db, whereClause, whereParams) {
  const sql = `
    SELECT e.upload_id, COUNT(*) as count 
    FROM events e 
    LEFT JOIN uploads u ON e.upload_id = u.id
    LEFT JOIN v_events2profile_indexed ei ON e.id = ei.event_id
    ${whereClause} 
    GROUP BY e.upload_id
  `;
  const rows = await db.exec(sql, {
    bind: whereParams,
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  const counts = {};
  rows.forEach(row => {
    counts[row.upload_id] = row.count;
  });
  return counts;
}

function _formatEventObject(row) {
  let attributes = {};
  let tags = [];
  let labels = [];
  let eventCategory = [];
  let eventType = [];
  let deviceProfilesData = [];
  
  try {
    attributes = row.attributes ? JSON.parse(row.attributes) : {};
  } catch (e) {
    console.warn('Failed to parse attributes:', e);
  }
  
  try {
    tags = row.tags ? JSON.parse(row.tags) : [];
  } catch (e) {
    console.warn('Failed to parse tags:', e);
  }
  
  try {
    labels = row.labels ? JSON.parse(row.labels) : [];
  } catch (e) {
    console.warn('Failed to parse labels:', e);
  }
  
  try {
    eventCategory = row.event_category ? JSON.parse(row.event_category) : [];
  } catch (e) {
    console.warn('Failed to parse event_category:', e);
  }
  
  try {
    eventType = row.event_type ? JSON.parse(row.event_type) : [];
  } catch (e) {
    console.warn('Failed to parse event_type:', e);
  }
  
  try {
    deviceProfilesData = row.device_profiles_data ? JSON.parse(row.device_profiles_data) : [];
  } catch (e) {
    console.warn('Failed to parse device_profiles_data:', e);
  }
  
  const source = {
    ...attributes,
    primary_timestamp: row.timestamp,
    timestamp: row.timestamp,
    message: row.message,
    category: eventCategory,
    type: eventType,
    event_action: row.event_action,
    event_kind: row.event_kind,
    tags,
    labels,
    timeline_name: row.timeline_name,
    timeline_id: row.upload_id,
    platform: row.platform,
    filename: row.source_file,
    device_profiles_data: deviceProfilesData,
  };
  
  return {
    _id: String(row.id),
    _index: row.upload_id,
    _source: source,
  };
}

export async function addLabelEvent(eventIds, labels) {
  if (!eventIds || eventIds.length === 0 || !labels || labels.length === 0) {
    return;
  }
  
  const db = await getDB();
  
  for (const eventId of eventIds) {
    const result = await db.exec(
      'SELECT labels FROM events WHERE id = ?',
      { bind: [eventId], returnValue: 'resultRows', rowMode: 'array' }
    );
    
    if (result.length === 0) continue;
    
    let currentLabels = [];
    try {
      currentLabels = result[0][0] ? JSON.parse(result[0][0]) : [];
    } catch (e) {
      console.error('[addLabelEvent] Failed to parse labels:', e);
      currentLabels = [];
    }
    
    const newLabels = [...new Set([...currentLabels, ...labels])];
    
    await db.exec(
      'UPDATE events SET labels = ? WHERE id = ?',
      { bind: [JSON.stringify(newLabels), eventId] }
    );
  }
}

export async function removeLabelEvent(eventIds, labels) {
  if (!eventIds || eventIds.length === 0 || !labels || labels.length === 0) {
    return;
  }
  
  const db = await getDB();
  
  for (const eventId of eventIds) {
    const result = await db.exec(
      'SELECT labels FROM events WHERE id = ?',
      { bind: [eventId], returnValue: 'resultRows', rowMode: 'array' }
    );
    
    if (result.length === 0) continue;
    
    let currentLabels = [];
    try {
      currentLabels = result[0][0] ? JSON.parse(result[0][0]) : [];
    } catch (e) {
      console.error('[removeLabelEvent] Failed to parse labels:', e);
      continue;
    }
    
    const newLabels = currentLabels.filter(label => !labels.includes(label));
    
    await db.exec(
      'UPDATE events SET labels = ? WHERE id = ?',
      { bind: [JSON.stringify(newLabels), eventId] }
    );
  }
}

export async function updateEventTags(eventId, tags) {
  const db = await getDB();
  
  await db.exec(
    'UPDATE events SET tags = ? WHERE id = ?',
    { bind: [JSON.stringify(tags || []), eventId] }
  );
}

