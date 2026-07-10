// added for WISPR-lab/data-export-gui
import { getDB } from '../index.js';
import { hexColor } from '@/utils/hex.js';

// Coerce epoch-zero timestamps to null so they never surface in the UI.
// Handles: 0, "0", 0.0, ISO strings starting with "1970-01-01".
function nullTs(val) {
  if (val === null || val === undefined) return null;
  var s = String(val).trim();
  if (s === '0' || s === '0.0' || s === '' || s.indexOf('1970-01-01') === 0) return null;
  var n = Number(val);
  if (!isNaN(n) && n === 0) return null;
  return val;
}

var EPOCH_ZERO_KEYS = ['entity_first_seen_timestamp', 'entity_last_seen_timestamp', 'timestamp'];

export async function getResolvedSessionsRegistrations() {
  const db = await getDB();
  
  const sql = `
    SELECT rsr.*, u.color as upload_color, u.platform as upload_platform
    FROM resolved_sessions_registrations rsr
    LEFT JOIN uploads u ON rsr.upload_id = u.id
  `;
  
  const rows = await db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });

  const resolved = [];

  for (const row of rows) {
    let attrs = {};
    if (row.attributes) {
      try {
        attrs = typeof row.attributes === 'string' ? JSON.parse(row.attributes) : row.attributes;
      } catch (e) {
        attrs = {};
      }
    }

    // Nullify epoch-zero on known timestamp keys in the attrs blob
    EPOCH_ZERO_KEYS.forEach(function(k) {
      if (k in attrs) attrs[k] = nullTs(attrs[k]);
    });

    const cookieVal = attrs['client_session_id'];
    const serialVal = attrs['device_serial_number'];

    let eventsQuery = '';
    let eventCount = 0;

    if (cookieVal) {
      eventsQuery = `cookie:${cookieVal}`;
      const pattern = String(cookieVal).replace(/\*/g, '%');
      const countSql = `
        SELECT COUNT(*) as count 
        FROM events 
        WHERE upload_id = ? 
          AND json_extract(attributes, '$.client_session_id') LIKE ?
      `;
      const countRes = await db.exec(countSql, {
        bind: [row.upload_id, pattern],
        returnValue: 'resultRows',
        rowMode: 'object'
      });
      eventCount = (countRes && countRes[0]) ? countRes[0].count : 0;

    } else if (serialVal) {
      eventsQuery = `serial:${serialVal}`;
      const pattern = String(serialVal).replace(/\*/g, '%');
      const countSql = `
        SELECT COUNT(*) as count 
        FROM events 
        WHERE upload_id = ? 
          AND json_extract(attributes, '$.device_serial_number') LIKE ?
      `;
      const countRes = await db.exec(countSql, {
        bind: [row.upload_id, pattern],
        returnValue: 'resultRows',
        rowMode: 'object'
      });
      eventCount = (countRes && countRes[0]) ? countRes[0].count : 0;
    }

    resolved.push({
      id: row.id,
      upload_id: row.upload_id,
      entity_type: row.entity_type,
      origin: row.origin,
      model_name: row.model_name || 'Unknown Device',
      client_name: row.client_name,
      os_name: row.os_name,
      os_version: row.os_version,
      os_type: row.os_type,
      is_reduced_ua: !!row.is_reduced_ua,
      user_agent_original: attrs['user_agent_original'] || null,
      has_trusted_cookie: !!row.has_trusted_cookie,
      trusted_cookie_id: row.trusted_cookie_id,
      has_passkey: !!row.has_passkey,
      registration_device: row.registration_device,
      upload_color: hexColor(row.upload_color),
      platform: row.upload_platform,
      attributes: attrs,
      events_query: eventsQuery,
      event_count: eventCount
    });
  }

  return resolved;
}
