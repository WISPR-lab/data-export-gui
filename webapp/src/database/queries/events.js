// custom to WISPR-lab/data-export-gui

import { getDB } from '../index.js';
import { buildWhereClause, buildOrderClause, buildPaginationClause } from '../whereClauseBuilder.js';

export async function searchEvents(queryString = '', filter = {}) {
  const db = await getDB();
  const { clause: whereClause, params: whereParams } = buildWhereClause({
    ...filter,
    query: queryString
  });
  const orderClause = buildOrderClause(filter);
  const { clause: paginationClause, params: paginationParams } = buildPaginationClause(filter);
  
  const sql = `
    SELECT 
      e.id, e.upload_id, e.timestamp, e.message, e.attributes, e.tags, e.labels,
      e.event_category, e.event_action, e.event_kind,
      f.opfs_filename as source_file, 
      u.given_name as timeline_name, u.platform
    FROM events e
    LEFT JOIN uploaded_files f ON json_extract(e.file_ids, '$[0]') = f.id
    LEFT JOIN uploads u ON e.upload_id = u.id
    ${whereClause}
    ${orderClause}
    ${paginationClause}
  `;
  
  const allParams = [...whereParams, ...paginationParams];
  
  const rows = await db.exec(sql, { 
    bind: allParams,
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  const totalCount = await _getEventsTotalCount(db, whereClause, whereParams);
  const countPerTimeline = await _getEventsCountPerTimeline(db, whereClause, whereParams);
  
  const objects = rows.map(row => _formatEventObject(row));
  
  return {
    objects,
    meta: {
      total_count: totalCount,
      count_per_timeline: countPerTimeline,
    }
  };
}

export async function getEventCount() {
  const db = await getDB();
  const result = await db.exec('SELECT COUNT(*) as count FROM events', {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  return (result[0] && result[0].count) || 0;
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
async function _getEventsTotalCount(db, whereClause, whereParams) {
  const sql = `SELECT COUNT(*) as count FROM events e ${whereClause}`;
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
  
  const source = {
    ...attributes,
    primary_timestamp: row.timestamp,
    timestamp: row.timestamp,
    message: row.message,
    category: eventCategory,
    event_action: row.event_action,
    event_kind: row.event_kind,
    tags,
    labels,
    timeline_name: row.timeline_name,
    timeline_id: row.upload_id,
    platform: row.platform,
    filename: row.source_file,
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
      { bind: [parseInt(eventId, 10)], returnValue: 'resultRows', rowMode: 'array' }
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
      { bind: [JSON.stringify(newLabels), parseInt(eventId, 10)] }
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
      { bind: [parseInt(eventId, 10)], returnValue: 'resultRows', rowMode: 'array' }
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
      { bind: [JSON.stringify(newLabels), parseInt(eventId, 10)] }
    );
  }
}

export async function updateEventTags(eventId, tags) {
  const db = await getDB();
  
  await db.exec(
    'UPDATE events SET tags = ? WHERE id = ?',
    { bind: [JSON.stringify(tags || []), parseInt(eventId, 10)] }
  );
}
