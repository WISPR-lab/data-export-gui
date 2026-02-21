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
      COALESCE(u.color, '5E75C2') as color,
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
  if (!uploadId) {
    console.error('[Uploads DB] No uploadId provided');
    return null;
  }
  const db = await getDB();
  
  const sql = `
    SELECT 
      u.id,
      u.given_name as name,
      u.platform,
      u.upload_timestamp as created_at,
      u.updated_at,
      COALESCE(u.color, '5E75C2') as color,
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
  
  const allowedFields = ['given_name', 'color'];
  const setClauses = [];
  const values = [];
  
  for (const [key, value] of Object.entries(updates)) {
    if (allowedFields.includes(key)) {
      setClauses.push(`${key} = ?`);
      values.push(value);
    }
  }
  
  if (setClauses.length === 0) {
    console.log('[uploadDB.updateUpload] No allowed fields found to update');
    return;
  }
  
  // Always update the updated_at timestamp
  setClauses.push('updated_at = ?');
  values.push(Date.now() / 1000);  // Convert to Unix timestamp (seconds)
  
  values.push(uploadId);  // uploadId is already a string UUID, don't parseInt it
  
  const sql = `UPDATE uploads SET ${setClauses.join(', ')} WHERE id = ?`;
  await db.exec(sql, { bind: values });
}

export async function deleteUpload(uploadId) {
  const db = await getDB();
  
  // Delete related data first (cascading deletes)
  await db.exec('DELETE FROM events WHERE upload_id = ?', { 
    bind: [uploadId]
  });
  
  await db.exec('DELETE FROM uploaded_files WHERE upload_id = ?', { 
    bind: [uploadId]
  });
  
  await db.exec('DELETE FROM raw_data WHERE upload_id = ?', { 
    bind: [uploadId]
  });
  
  // Finally delete the upload record
  await db.exec('DELETE FROM uploads WHERE id = ?', { 
    bind: [uploadId]
  });
}
