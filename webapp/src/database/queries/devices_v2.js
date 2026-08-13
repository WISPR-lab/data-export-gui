// added for WISPR-lab/data-export-gui
import { getDB } from '../index.js';
import { hexColor } from '@/utils/hex.js';
import { getUASummary } from './ua_summary.js';

export async function getUnlinkedClusters() {
  const db = await getDB();
  
  const sql = `
    SELECT di.*, u.color as upload_color, u.platform as upload_platform
    FROM device_instances di
    LEFT JOIN uploads u ON di.upload_id = u.id
    ORDER BY di.last_seen DESC
  `;
  
  const rows = await db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });

  const formatDate = (ts) => {
    if (!ts) return '';
    const date = new Date(ts * 1000);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return rows.map(row => {
    let start = formatDate(row.first_seen);
    let end = formatDate(row.last_seen);
    let dateStr = start;
    if (start && end && start !== end) {
      dateStr = `${start} – ${end}`;
    }

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
      dateString: dateStr || '',
      event_count: row.event_count || 0,
      query: 'device_instance_id:' + row.id,
      upload_color: hexColor(row.upload_color)
    };
  });
}
