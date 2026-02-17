// custom to WISPR-lab/data-export-gui

import { getDB } from '../index.js';

export async function getEventComments(eventId) {
  const db = await getDB();
  
  const sql = `
    SELECT id, event_id, comment, created_at, updated_at
    FROM event_comments
    WHERE event_id = ?
    ORDER BY created_at ASC
  `;
  
  const rows = await db.exec(sql, {
    bind: [parseInt(eventId, 10)],
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  return rows || [];
}

export async function addEventComment(eventId, commentText) {
  const db = await getDB();
  
  const now = new Date().toISOString();
  const sql = `
    INSERT INTO event_comments (event_id, comment, created_at, updated_at)
    VALUES (?, ?, ?, ?)
  `;
  
  await db.exec(sql, {
    bind: [parseInt(eventId, 10), commentText, now, now]
  });
  
  const result = await db.exec('SELECT last_insert_rowid() as id', {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  return {
    id: (result[0] && result[0].id) || null,
    event_id: eventId,
    comment: commentText,
    created_at: now,
    updated_at: now
  };
}

export async function updateEventComment(commentId, newText) {
  const db = await getDB();
  
  const now = new Date().toISOString();
  const sql = `
    UPDATE event_comments
    SET comment = ?, updated_at = ?
    WHERE id = ?
  `;
  
  await db.exec(sql, {
    bind: [newText, now, parseInt(commentId, 10)]
  });
  
  const result = await db.exec('SELECT * FROM event_comments WHERE id = ?', {
    bind: [parseInt(commentId, 10)],
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  return result[0] || null;
}

export async function deleteEventComment(commentId) {
  const db = await getDB();
  
  const sql = 'DELETE FROM event_comments WHERE id = ?';
  await db.exec(sql, {
    bind: [parseInt(commentId, 10)]
  });
}
