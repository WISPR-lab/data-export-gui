import { getDB } from '../index.js';

/**
 * Fetches all device groups and joins with a representative auth_device
 * to display basic properties.
 */
export async function getDeviceGroups() {
  const db = await getDB();
  
  const deviceSql = `SELECT * FROM device_profiles`;
  const uploadSql = `SELECT id, color FROM uploads`;
  
  const deviceRows = await db.exec(deviceSql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });

  const uploadRows = await db.exec(uploadSql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });

  // Create map of upload_id -> color for quick lookup
  const uploadColorMap = {};
  uploadRows.forEach(row => {
    uploadColorMap[row.id] = row.color;
  });

  return deviceRows.map(row => {
    let attrs = {};
    let origins = [];
    try {
      attrs = row.attributes ? JSON.parse(row.attributes) : {};
      origins = row.origins ? JSON.parse(row.origins) : [];
    } catch (e) {
      console.warn('Failed to parse attributes/origins for device group', row.id);
    }

    // Enrich origins with color information
    const enrichedOrigins = Array.isArray(origins) ? origins.map(origin => {
      if (typeof origin === 'string') {
        // If origins is just strings, we don't have upload_id mapping
        return { origin, upload_id: null, color: null };
      }
      // If origins already has upload_id, look up the color
      return {
        ...origin,
        color: origin.upload_id ? uploadColorMap[origin.upload_id] : null
      };
    }) : [];

    return {
      id: row.id,
      atomic_devices_ids: row.atomic_devices_ids ? JSON.parse(row.atomic_devices_ids) : [],
      model: row.model || '',
      is_generic: !!row.is_generic,
      user_label: row.user_label,
      notes: row.notes || '',
      origins: enrichedOrigins,
      attributes: attrs,
      label: row.user_label || row.model || attrs.device_model_name || 'Unknown Device',
      manufacturer: attrs.device_manufacturer || 'TODO: Get from merged attributes',
      os: (attrs.os_name || '') + ' ' + (attrs.os_version || '') || 'TODO: Get from merged attributes',
      city: 'TODO: Calculate from geographic events',
      // Metadata for UI
      system_soft_merge: !!row.system_soft_merge
    };
  });
} // TODO merge bttons on device;  need OS infroamtion, history, geolocation, etc. to make this useful

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

