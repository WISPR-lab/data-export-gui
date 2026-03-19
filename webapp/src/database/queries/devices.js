import { getDB } from '../index.js';

/**
 * Fetches all device groups and joins with a representative auth_device
 * to display basic properties.
 */
export async function getDeviceGroups() {
  const db = await getDB();
  
  // Note: Since we haven't decided on cross-device attribute merging yet,
  // we pick attributes from the first auth_device in the group.
  const sql = `
    SELECT 
      dg.*,
      ad.attributes as raw_attributes,
      ad.origins as raw_origins
    FROM device_profiles dg
    LEFT JOIN atomic_devices ad ON json_extract(dg.atomic_devices_ids, '$[0]') = ad.id
  `;
  
  const rows = await db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });

  return rows.map(row => {
    let attrs = {};
    let origins = [];
    try {
      attrs = JSON.parse(row.raw_attributes || '{}');
      origins = JSON.parse(row.raw_origins || '[]');
    } catch (e) {
      console.warn('Failed to parse attributes for device group', row.id);
    }

    return {
      id: row.id,
      atomic_devices_ids: JSON.parse(row.atomic_devices_ids || '[]'),
      best_model: row.best_model || '',
      is_generic: !!row.is_generic,
      user_label: row.user_label,
      notes: row.notes || '',
      // Origins from the first atomic_device in the group
      origins: origins,
      // Placeholder fields for future Python-calculated merged attributes
      label: row.user_label || row.best_model || attrs.device_model_name || 'Unknown Device',
      manufacturer: attrs.device_manufacturer || 'TODO: Get from merged attributes',
      os: (attrs.os_name || '') + ' ' + (attrs.os_version || '') || 'TODO: Get from merged attributes',
      city: 'TODO: Calculate from geographic events',
      notes: row.labels ? JSON.parse(row.labels).join(', ') : '',
      // Metadata for UI
      system_soft_merge: !!row.system_soft_merge,
      is_generic: !!row.is_generic
    };
  });
}

export async function updateDeviceGroup(groupId, updates) {
  const db = await getDB();
  
  const allowed = ['user_label', 'notes'];
  const keys = Object.keys(updates).filter(k => allowed.includes(k));
  
  if (keys.length === 0) return;
  
  const setClause = keys.map(k => `${k} = ?`).join(', ');
  const params = [...keys.map(k => updates[k]), groupId];
  
  const sql = `UPDATE device_profiles SET ${setClause}, updated_at = ? WHERE id = ?`;
  params.splice(params.length - 1, 0, Date.now() / 1000);

  await db.exec(sql, { bind: params });
}

