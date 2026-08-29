// custom to anonymous-research-group/data-export-gui

import { getDB } from '../index.js';
import { buildWhereClause, buildOrderClause, buildPaginationClause } from './eventQueryBuilder.js';
import { getLogger } from '@/utils/logger.js';

const logger = getLogger('EventQueries');

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
      { type: 'attribute', field: 'user_agent_os_name', value: 'Windows' },
      { type: 'label', value: 'verified' },
      { type: 'datetime:range', value: '2024-01-15T00:00:00Z,2024-01-20T23:59:59Z' }
    ]
  }
*/

export async function searchEvents(dbName, queryString = '', filter = {}) {
  /* Builds WHERE/ORDER/PAGINATION, batch-resolves file refs and raw_data line numbers, returns Elasticsearch-shaped {_id, _index, _source} hit objects. */
  const db = await getDB(dbName);
  
  const stringColumns = ['e.id', 'e.upload_id', 'e.event_type_msg', 'e.event_category', 'e.event_action', 'e.event_kind', 'dg.model', 'dge.device_group_id', 'u.platform'];
  
  const orderClause = buildOrderClause(filter);
  const { clause: paginationClause, params: paginationParams } = buildPaginationClause(filter);
  const { clause: whereClause, params: whereParams } = buildWhereClause(filter, queryString, stringColumns);
  
  const sql = `
    SELECT 
      e.id, 
      e.upload_id, 
      e.timestamp, 
      e.event_type_msg, 
      e.attributes, 
      e.tags, 
      e.labels,
      e.event_category, 
      e.event_type, 
      e.event_action, 
      e.event_kind,
      e.file_ids,
      e.raw_data_ids,
      e.starred,
      u.given_name AS data_export_name,
      u.platform AS platform,
      dg.model AS device_model,
      dge.device_group_id,
      COUNT(*) OVER () AS total_count
    FROM events e
    LEFT JOIN uploads u ON e.upload_id = u.id
    LEFT JOIN device_group_events dge ON e.id = dge.event_id
    LEFT JOIN device_groups dg ON dge.device_group_id = dg.id
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
    logger.debug(`Executed SQL: ${sql}`);
    logger.debug(`With params: ${JSON.stringify(allParams)}`);

    // total_count comes from the window function — same scan as the page query, no extra round-trip
    const totalCount = (rows.length > 0 && rows[0].total_count) ? rows[0].total_count : 0;
    const countPerDataExport = await _getEventsCountPerTimeline(db, whereClause, whereParams);
    const countPerEventType = await _getEventsCountPerEventType(db, whereClause, whereParams);
    const countPerIPAddress = await _getEventsCountPerIPAddress(db, whereClause, whereParams);
    const countPerTagOrLabel = await _getEventsCountPerTagOrLabel(db, filter, queryString);
    
    // Batch resolve files and line numbers
    const allFileIds = new Set();
    const allRawDataIds = new Set();
    rows.forEach(row => {
      try {
        const fileIds = row.file_ids ? JSON.parse(row.file_ids) : [];
        fileIds.forEach(id => { if (id) allFileIds.add(id); });
      } catch (e) {}
      try {
        const rawDataIds = row.raw_data_ids ? JSON.parse(row.raw_data_ids) : [];
        rawDataIds.forEach(id => { if (id) allRawDataIds.add(id); });
      } catch (e) {}
    });

    const fileMap = {};
    if (allFileIds.size > 0) {
      const fileIdList = [...allFileIds];
      const placeholders = fileIdList.map(() => '?').join(',');
      const fileRows = await db.exec(`SELECT id, opfs_filename FROM uploaded_files WHERE id IN (${placeholders})`, {
        bind: fileIdList,
        returnValue: 'resultRows',
        rowMode: 'object'
      });
      fileRows.forEach(fileRow => {
        fileMap[fileRow.id] = fileRow.opfs_filename;
      });
    }

    const rawDataMap = {};
    if (allRawDataIds.size > 0) {
      const rawDataIdList = [...allRawDataIds];
      const placeholders = rawDataIdList.map(() => '?').join(',');
      const rawRows = await db.exec(`SELECT id, file_id, line_numbers FROM raw_data WHERE id IN (${placeholders})`, {
        bind: rawDataIdList,
        returnValue: 'resultRows',
        rowMode: 'object'
      });
      rawRows.forEach(rawRow => {
        let lines = [];
        try {
          lines = rawRow.line_numbers ? JSON.parse(rawRow.line_numbers) : [];
        } catch (e) {}
        rawDataMap[rawRow.id] = { file_id: rawRow.file_id, lines };
      });
    }

    const objects = rows.map(row => {
      let fileIds = [];
      let rawDataIds = [];
      try {
        fileIds = row.file_ids ? JSON.parse(row.file_ids) : [];
      } catch (e) {}
      try {
        rawDataIds = row.raw_data_ids ? JSON.parse(row.raw_data_ids) : [];
      } catch (e) {}

      const filenames = [...new Set(fileIds.map(fid => fileMap[fid]).filter(Boolean))];

      // map file to. lines
      const sourcesInfo = [];
      const flatLineNumbers = [];
      rawDataIds.forEach(rid => {
        const rd = rawDataMap[rid];
        if (rd) {
          const fname = fileMap[rd.file_id] || 'Unknown File';
          sourcesInfo.push({
            filename: fname,
            line_numbers: rd.lines
          });
          flatLineNumbers.push(...rd.lines);
        }
      });

      return _formatEventObject(row, filenames, [...new Set(flatLineNumbers)], sourcesInfo);
    });
    
    logger.debug(`[Search] "${queryString}" --> ${totalCount} results`);
    return {
      objects,
      meta: {
        total_count: totalCount,
        count_per_data_export: countPerDataExport,
        count_per_event_type: countPerEventType,
        count_per_ip_address: countPerIPAddress,
        count_per_tag_or_label: countPerTagOrLabel,
      }
    };
  } catch (error) {
    console.error('[searchEvents] ERROR:', error);
    throw error;
  }
}

export async function getEventCount(dbName) {
  const db = await getDB(dbName);
  const result = await db.exec('SELECT COUNT(*) as count FROM events', {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  const count = (result[0] && result[0].count) || 0;
  logger.debug('[getEventCount] Total events in DB:', count);
  return count;
}

export async function deleteEvents(dbName, eventIds) {
  const db = await getDB(dbName);
  
  const ids = Array.isArray(eventIds) ? eventIds : [eventIds];
  if (ids.length === 0) return;
  
  const placeholders = ids.map(() => '?').join(',');
  const sql = `DELETE FROM events WHERE id IN (${placeholders})`;
  
  await db.exec(sql, { bind: ids });
}

// Note: Frontend uses event_action field (from manifest view static fields).
// The event_category field (ECS event.category) is not used in UI filtering.

export async function getEventActions(dbName) {
  const db = await getDB(dbName);
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


export async function getEventTypes(dbName) {
  const db = await getDB(dbName);
  const sql = `
    SELECT event_type_msg, COUNT(*) as count 
    FROM events 
    WHERE event_type_msg IS NOT NULL AND event_type_msg != ''
    GROUP BY event_type_msg 
    ORDER BY count DESC
  `;
  
  const rows = await db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  if (rows.length === 0) {
      console.warn('[getEventTypes] No event type messages found in the database.');
  }

  return rows.map(row => ({
    event_type_msg: row.event_type_msg,
    count: row.count
  }));
}



export async function getEventTags(dbName) {
  /* SQL-side aggregation via json_each — avoids loading all tag blobs into the WASM heap. */
  const db = await getDB(dbName);
  const sql = `
    SELECT j.value AS tag, COUNT(*) AS count
    FROM events
    JOIN json_each(events.tags) j
    WHERE events.tags IS NOT NULL AND events.tags != '' AND events.tags != '[]'
    GROUP BY j.value
    ORDER BY count DESC
  `;
  const rows = await db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  return rows.map(function(row) { return { tag: row.tag, count: row.count }; });
}

export async function getIPAddresses(dbName) {
  const db = await getDB(dbName);
  const sql = `
    SELECT json_extract(attributes, '$.client_ip') AS client_ip, COUNT(*) AS count
    FROM events
    WHERE json_extract(attributes, '$.client_ip') IS NOT NULL
    GROUP BY client_ip
    ORDER BY count DESC
  `;
  const rows = await db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  return rows.map(function(row) { return { client_ip: row.client_ip, count: row.count }; });
}

async function _getEventsCountPerTimeline(db, whereClause, whereParams) {
  const sql = `
    SELECT e.upload_id, COUNT(*) as count 
    FROM events e
    LEFT JOIN uploads u ON e.upload_id = u.id
    LEFT JOIN device_group_events dge ON e.id = dge.event_id
    LEFT JOIN device_groups dg ON dge.device_group_id = dg.id
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

async function _getEventsCountPerEventType(db, whereClause, whereParams) {
  // Compute counts with the current filter
  const baseWhere = 'WHERE e.event_type_msg IS NOT NULL AND e.event_type_msg != \'\'';
  const combinedWhere = whereClause ? whereClause + ' AND e.event_type_msg IS NOT NULL AND e.event_type_msg != \'\'': baseWhere;
  const sql = `
    SELECT e.event_type_msg, COUNT(*) as count 
    FROM events e
    LEFT JOIN uploads u ON e.upload_id = u.id
    LEFT JOIN device_group_events dge ON e.id = dge.event_id
    LEFT JOIN device_groups dg ON dge.device_group_id = dg.id
    ${combinedWhere}
    GROUP BY e.event_type_msg
  `;
  const rows = await db.exec(sql, { 
    bind: whereParams,
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  const counts = {};
  rows.forEach(row => {
    counts[row.event_type_msg] = row.count;
  });
  return counts;
}

async function _getEventsCountPerIPAddress(db, whereClause, whereParams) {
  const ipCondition = "json_extract(e.attributes, '$.client_ip') IS NOT NULL";
  const combinedWhere = whereClause
    ? whereClause + ' AND ' + ipCondition
    : 'WHERE ' + ipCondition;
  const sql = `
    SELECT json_extract(e.attributes, '$.client_ip') AS client_ip, COUNT(*) AS count
    FROM events e
    LEFT JOIN uploads u ON e.upload_id = u.id
    LEFT JOIN device_group_events dge ON e.id = dge.event_id
    LEFT JOIN device_groups dg ON dge.device_group_id = dg.id
    ${combinedWhere}
    GROUP BY client_ip
  `;
  const rows = await db.exec(sql, {
    bind: whereParams,
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  const ipCounts = {};
  rows.forEach(function(row) {
    if (row.client_ip) ipCounts[row.client_ip] = row.count;
  });
  return ipCounts;
}

async function _getEventsCountPerTagOrLabel(db, filter, queryString) {
  // Strip tag/label chips so their own filter doesn't exclude them from the count
  const stringColumns = ['e.id', 'e.upload_id', 'e.event_type_msg', 'e.event_category', 'e.event_action', 'e.event_kind', 'u.platform'];
  const filteredChips = (filter.chips || []).filter(function(c) { return c.type !== 'tag' && c.type !== 'label'; });
  const modifiedFilter = Object.assign({}, filter, { chips: filteredChips });
  const { clause: whereClause, params: whereParams } = buildWhereClause(modifiedFilter, queryString || '', stringColumns);

  // Push aggregation to SQL via json_each — one query per column, merge in JS
  function makeQuery(col) {
    return `
      SELECT j.value AS item, COUNT(*) AS count
      FROM events e
      LEFT JOIN uploads u ON e.upload_id = u.id
      LEFT JOIN device_group_events dge ON e.id = dge.event_id
      JOIN json_each(e.${col}) j
      ${whereClause}
      GROUP BY j.value
    `;
  }

  const counts = {};
  var tagRows = await db.exec(makeQuery('tags'), { bind: whereParams, returnValue: 'resultRows', rowMode: 'object' });
  tagRows.forEach(function(row) { if (row.item) counts[row.item] = (counts[row.item] || 0) + row.count; });
  var labelRows = await db.exec(makeQuery('labels'), { bind: whereParams, returnValue: 'resultRows', rowMode: 'object' });
  labelRows.forEach(function(row) { if (row.item) counts[row.item] = (counts[row.item] || 0) + row.count; });
  return counts;
}

function _formatEventObject(row, filenames = [], lineNumbers = [], sources = []) {
  /* Transforms a DB row into Elasticsearch-compatible {_id, _index, _source} format, parsing 6 JSON fields with fallback defaults. */
  let attributes = {};
  let tags = [];
  let labels = [];
  let eventCategory = [];
  let eventType = [];

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
  
  const source = {
    ...attributes,
    primary_timestamp: row.timestamp,
    timestamp: row.timestamp,
    event_type_msg: row.event_type_msg,
    category: eventCategory,
    type: eventType,
    event_action: row.event_action,
    event_kind: row.event_kind,
    tags,
    labels,
    data_export_name: row.data_export_name,
    data_export_id: row.upload_id,
    platform: row.platform,
    starred: row.starred || 0,
    filename: filenames[0] || '',
    filenames,
    line_numbers: lineNumbers,
    sources,
    device_model: row.device_model || '',
    ...(row.device_group_id ? { device_group_id: row.device_group_id } : {})
  };
  
  return {
    _id: String(row.id),
    _index: row.upload_id,
    _source: source,
  };
}

export async function addLabelEvent(dbName, eventIds, labels) {
  /* Per-row read-modify-write: reads current JSON labels, merges new ones (deduped), writes back. Not batched. */
  if (!eventIds || eventIds.length === 0 || !labels || labels.length === 0) {
    return;
  }

  const db = await getDB(dbName);
  
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
    const isStarred = labels.includes('starred') ? 1 : 0;
    
    if (isStarred) {
      await db.exec(
        'UPDATE events SET labels = ?, starred = 1 WHERE id = ?',
        { bind: [JSON.stringify(newLabels), eventId] }
      );
    } else {
      await db.exec(
        'UPDATE events SET labels = ? WHERE id = ?',
        { bind: [JSON.stringify(newLabels), eventId] }
      );
    }
  }
}

export async function removeLabelEvent(dbName, eventIds, labels) {
  /* Per-row read-modify-write: reads current JSON labels, filters out specified ones, writes back. Not batched. */
  if (!eventIds || eventIds.length === 0 || !labels || labels.length === 0) {
    return;
  }

  const db = await getDB(dbName);
  
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
    const wasStarredRemoved = labels.includes('starred') ? 1 : 0;
    
    if (wasStarredRemoved) {
      await db.exec(
        'UPDATE events SET labels = ?, starred = 0 WHERE id = ?',
        { bind: [JSON.stringify(newLabels), eventId] }
      );
    } else {
      await db.exec(
        'UPDATE events SET labels = ? WHERE id = ?',
        { bind: [JSON.stringify(newLabels), eventId] }
      );
    }
  }
}

export async function updateEventTags(dbName, eventId, tags) {
  const db = await getDB(dbName);
  
  await db.exec(
    'UPDATE events SET tags = ? WHERE id = ?',
    { bind: [JSON.stringify(tags || []), eventId] }
  );
}

export async function clearAllTags(dbName) {
  const db = await getDB(dbName);
  logger.debug('[Database] Clearing all tags from events');
  await db.exec("UPDATE events SET tags = '[]'");
}

export async function addTagToEventsQuery(dbName, eventsQuery, tag, remove = false) {
  if (!eventsQuery || !tag) return 0;
  const db = await getDB(dbName);
  let eventsToUpdate = [];

  if (eventsQuery.indexOf('client_session_id:') !== -1) {
    var sid = eventsQuery.replace('client_session_id:', '').replace(/"/g, '');
    var pattern = String(sid).replace(/\*/g, '%');
    eventsToUpdate = await db.exec(
      `SELECT id, tags FROM events WHERE json_extract(attributes, '$.client_session_id') LIKE ?`,
      { bind: [pattern], returnValue: 'resultRows', rowMode: 'object' }
    );
  } else if (eventsQuery.indexOf('device_serial_number:') !== -1) {
    var serial = eventsQuery.replace('device_serial_number:', '').replace(/"/g, '');
    var pattern2 = String(serial).replace(/\*/g, '%');
    eventsToUpdate = await db.exec(
      `SELECT id, tags FROM events WHERE json_extract(attributes, '$.device_serial_number') LIKE ?`,
      { bind: [pattern2], returnValue: 'resultRows', rowMode: 'object' }
    );
  } else if (eventsQuery.indexOf('device_group_id:') !== -1) {
    var groupId = eventsQuery.replace('device_group_id:', '').replace(/"/g, '');
    eventsToUpdate = await db.exec(
      `SELECT e.id, e.tags FROM events e JOIN device_group_events dge ON e.id = dge.event_id WHERE dge.device_group_id = ?`,
      { bind: [groupId], returnValue: 'resultRows', rowMode: 'object' }
    );
  } else if (eventsQuery.indexOf('client_ip:') !== -1) {
    var ip = eventsQuery.replace('client_ip:', '').replace(/"/g, '');
    eventsToUpdate = await db.exec(
      `SELECT id, tags FROM events WHERE json_extract(attributes, '$.client_ip') = ?`,
      { bind: [ip], returnValue: 'resultRows', rowMode: 'object' }
    );
  }

  let changedCount = 0;
  if (eventsToUpdate && eventsToUpdate.length > 0) {
    for (const ev of eventsToUpdate) {
      let currentTags = [];
      try {
        currentTags = typeof ev.tags === 'string' ? JSON.parse(ev.tags || '[]') : (ev.tags || []);
      } catch (e) {
        currentTags = [];
      }
      let newTags = [...currentTags];
      if (remove) {
        newTags = newTags.filter(t => t !== tag);
      } else {
        if (!newTags.includes(tag)) {
          newTags.push(tag);
        }
      }
      if (JSON.stringify(newTags) !== JSON.stringify(currentTags)) {
        await db.exec('UPDATE events SET tags = ? WHERE id = ?', { bind: [JSON.stringify(newTags), ev.id] });
        changedCount++;
      }
    }
  }
  return changedCount;
}

