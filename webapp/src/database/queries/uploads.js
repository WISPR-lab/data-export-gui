// custom to WISPR-lab/data-export-gui

import { getDB } from '../index.js';

export async function getUploads() {
  const db = await getDB();
  
  const sql = `
    SELECT 
      u.id,
      u.given_name as name,
      u.platform,
      u.upload_timestamp as created_at,
      u.color,
      'ready' as status,
      COUNT(e.id) as event_count
    FROM upload u
    LEFT JOIN events e ON e.upload_id = u.id
    GROUP BY u.id
    ORDER BY u.upload_timestamp DESC
  `;
  
  const rows = db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  return {
    data: {
      objects: rows || []
    }
  };
}

export async function getUploadById(uploadId) {
  const db = await getDB();
  
  const sql = `
    SELECT 
      u.id,
      u.given_name as name,
      u.platform,
      u.upload_timestamp as created_at,
      u.color,
      'ready' as status,
      COUNT(e.id) as event_count
    FROM upload u
    LEFT JOIN events e ON e.upload_id = u.id
    WHERE u.id = ?
    GROUP BY u.id
  `;
  
  const rows = db.exec(sql, {
    bind: [parseInt(uploadId, 10)],
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  return rows.length > 0 ? rows[0] : null;
}
