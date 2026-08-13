// added for WISPR-lab/data-export-gui
import { getDB } from '../index.js';
import { hexColor } from '@/utils/hex.js';
import { getUASummary } from './ua_summary.js';

export async function getUnlinkedGroups() {
  const db = await getDB();
  
  const sql = `
    SELECT dg.*, u.color as upload_color, u.platform as upload_platform
    FROM device_groups dg
    LEFT JOIN uploads u ON dg.upload_id = u.id
    ORDER BY dg.last_seen DESC
  `;
  
  const rows = await db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });

  return rows.map(row => {
    var summary = getUASummary([row])[0] || {};
    var clientLabel = summary.primary ? (summary.primary + (summary.secondary ? ' (' + summary.secondary + ')' : '')) : row.client_name;

    return {
      ...row,
      id: row.id,
      upload_id: row.upload_id,
      platform: row.upload_platform,
      title: row.model || 'Unknown Device',
      norm_client: clientLabel,
      os_type: row.os_type || null,
      first_seen: row.first_seen || null,
      last_seen: row.last_seen || null,
      event_count: row.event_count || 0,
      query: 'device_group_id:' + row.id,
      upload_color: hexColor(row.upload_color)
    };
  });
}
