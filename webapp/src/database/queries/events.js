// custom to WISPR-lab/data-export-gui

import { getDB } from '../index.js';
import { buildWhereClause, buildOrderClause, buildPaginationClause } from '../where_clause_builder.js';

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
      e.category, e.event_kind,
      f.opfs_filename as source_file, 
      u.given_name as timeline_name
    FROM events e
    LEFT JOIN uploaded_files f ON json_extract(e.file_ids, '$[0]') = f.id
    LEFT JOIN upload u ON e.upload_id = u.id
    ${whereClause}
    ${orderClause}
    ${paginationClause}
  `;
  
  const allParams = [...whereParams, ...paginationParams];
  
  const rows = db.exec(sql, { 
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
  const result = db.exec('SELECT COUNT(*) as count FROM events', {
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
  
  db.exec(sql, { bind: ids });
}

async function _getEventsTotalCount(db, whereClause, whereParams) {
  const sql = `SELECT COUNT(*) as count FROM events e ${whereClause}`;
  const result = db.exec(sql, {
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
  const rows = db.exec(sql, {
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
  
  const source = {
    ...attributes,
    primary_timestamp: row.timestamp,
    timestamp: row.timestamp,
    message: row.message,
    category: row.category,
    event_kind: row.event_kind,
    tags,
    labels,
    timeline_name: row.timeline_name,
    timeline_id: row.upload_id,
    filename: row.source_file,
  };
  
  return {
    _id: String(row.id),
    _index: row.upload_id,
    _source: source,
  };
}
