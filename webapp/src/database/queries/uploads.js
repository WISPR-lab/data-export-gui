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
      u.updated_at,
      u.color,
      'ready' as status,
      COUNT(e.id) as event_count
    FROM uploads u
    LEFT JOIN events e ON e.upload_id = u.id
    GROUP BY u.id
    ORDER BY u.upload_timestamp DESC
  `;
  
  const rows = await db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  return {
    objects: rows || []
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
      u.updated_at,
      u.color,
      'ready' as status,
      COUNT(e.id) as event_count
    FROM uploads u
    LEFT JOIN events e ON e.upload_id = u.id
    WHERE u.id = ?
    GROUP BY u.id
  `;
  
  const rows = await db.exec(sql, {
    bind: [parseInt(uploadId, 10)],
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  return rows.length > 0 ? rows[0] : null;
}

export async function updateUpload(uploadId, updates) {
  const db = await getDB();
  
  const allowedFields = ['given_name', 'color', 'description'];
  const setClauses = [];
  const values = [];
  
  for (const [key, value] of Object.entries(updates)) {
    if (allowedFields.includes(key)) {
      setClauses.push(`${key} = ?`);
      values.push(value);
    }
  }
  
  if (setClauses.length === 0) {
    return;
  }
  
  // Always update the updated_at timestamp
  setClauses.push('updated_at = ?');
  values.push(Date.now() / 1000);  // Convert to Unix timestamp (seconds)
  
  values.push(parseInt(uploadId, 10));
  
  const sql = `UPDATE uploads SET ${setClauses.join(', ')} WHERE id = ?`;
  db.exec(sql, { bind: values });
}

export async function deleteUpload(uploadId) {
  const db = await getDB();
  
  // Delete related data first (cascading deletes)
  db.exec('DELETE FROM events WHERE upload_id = ?', { 
    bind: [parseInt(uploadId, 10)] 
  });
  
  db.exec('DELETE FROM uploaded_files WHERE upload_id = ?', { 
    bind: [parseInt(uploadId, 10)] 
  });
  
  db.exec('DELETE FROM raw_data WHERE upload_id = ?', { 
    bind: [parseInt(uploadId, 10)] 
  });
  
  // Finally delete the upload record
  db.exec('DELETE FROM uploads WHERE id = ?', { 
    bind: [parseInt(uploadId, 10)] 
  });
}
