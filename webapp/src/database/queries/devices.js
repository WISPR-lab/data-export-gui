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
    let color = row.color ? String(row.color) : '#999999';
    if (color.length > 0 && color[0] !== '#') {
      color = '#' + color;
    }
    uploadColorMap[row.id] = color;
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
        return { origin, upload_id: null, color: null };
      }
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
      os_name: attrs.device_os_name || attrs.user_agent_os_name || attrs.device_os_type || attrs.user_agent_os_type || '',
      os_version: attrs.device_os_version || attrs.user_agent_os_version || '',
      label: row.user_label || row.model || attrs.device_model_name || 'Unknown Device',
      manufacturer: attrs.device_manufacturer || 'TODO: Get from merged attributes',
      city: 'TODO: Calculate from geographic events',
      // Metadata for UI
      system_soft_merge: !!row.system_soft_merge
    };
  });
} // TODO merge bttons on device;  need OS infroamtion, history, geolocation, etc. to make this useful

export async function getAtomicDevices(atomicIds) {
  const db = await getDB();
  
  if (!atomicIds || atomicIds.length === 0) return [];
  
  const uploadSql = `SELECT id, color, platform FROM uploads`;
  const uploadRows = await db.exec(uploadSql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  const uploadColorMap = {};
  uploadRows.forEach(row => {
    let color = row.color ? String(row.color) : '#999999';
    if (color.length > 0 && color[0] !== '#') {
      color = '#' + color;
    }
    uploadColorMap[row.id] = { color: color, platform: row.platform };
  });
  
  const placeholders = atomicIds.map(() => '?').join(',');
  const atomicSql = `SELECT * FROM atomic_devices WHERE id IN (${placeholders})`;
  
  const atomicRows = await db.exec(atomicSql, {
    bind: atomicIds,
    returnValue: 'resultRows',
    rowMode: 'object'
  });

  return atomicRows.map(row => {
    let attrs = {};
    let uploadIds = [];
    let origins = [];
    
    try {
      attrs = row.attributes ? JSON.parse(row.attributes) : {};
      uploadIds = row.upload_ids ? JSON.parse(row.upload_ids) : [];
      origins = row.origins ? JSON.parse(row.origins) : [];
    } catch (e) {
      console.warn('Failed to parse atomic device', row.id, e);
    }

    const primaryUploadId = uploadIds[0];
    const uploadInfo = primaryUploadId ? uploadColorMap[primaryUploadId] : null;
    
    return {
      id: row.id,
      upload_ids: uploadIds,
      origins: origins,
      attributes: attrs,
      specificity: row.specificity,
      model: attrs.device_model_name || attrs.user_agent_device_model || 'Unknown Device',
      uploadPlatform: uploadInfo ? uploadInfo.platform : 'Unknown',
      uploadColor: uploadInfo ? uploadInfo.color : '#999999'
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

export async function getDevices() {
  const db = await getDB();
  
  // Fetch profiles
  const deviceSql = `SELECT * FROM device_profiles`;
  const deviceRows = await db.exec(deviceSql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });

  // Collect all atomic IDs from all profiles
  const allAtomicIds = [];
  deviceRows.forEach(row => {
    const ids = row.atomic_devices_ids ? JSON.parse(row.atomic_devices_ids) : [];
    allAtomicIds.push(...ids);
  });

  // Fetch uploads for coloring
  const uploadSql = `SELECT id, color, platform FROM uploads`;
  const uploadRows = await db.exec(uploadSql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  const uploadColorMap = {};
  uploadRows.forEach(row => {
    let color = row.color ? String(row.color) : '#999999';
    if (color.length > 0 && color[0] !== '#') {
      color = '#' + color;
    }
    uploadColorMap[row.id] = { color: color, platform: row.platform };
  });

  // Fetch all atomics at once
  let atomicsMap = {};
  if (allAtomicIds.length > 0) {
    const placeholders = allAtomicIds.map(() => '?').join(',');
    const atomicSql = `SELECT * FROM atomic_devices WHERE id IN (${placeholders})`;
    
    const atomicRows = await db.exec(atomicSql, {
      bind: allAtomicIds,
      returnValue: 'resultRows',
      rowMode: 'object'
    });

    atomicRows.forEach(row => {
      let attrs = {};
      let uploadIds = [];
      let origins = [];
      
      try {
        attrs = row.attributes ? JSON.parse(row.attributes) : {};
        uploadIds = row.upload_ids ? JSON.parse(row.upload_ids) : [];
        origins = row.origins ? JSON.parse(row.origins) : [];
      } catch (e) {
        console.warn('Failed to parse atomic device', row.id, e);
      }

      const primaryUploadId = uploadIds[0];
      const uploadInfo = primaryUploadId ? uploadColorMap[primaryUploadId] : null;
      
      // Enrich origins with colors
      const enrichedOrigins = Array.isArray(origins) ? origins.map(origin => {
        if (typeof origin === 'string') {
          return { origin, upload_id: null, color: null };
        }
        let color = null;
        if (origin.upload_id) {
          const uploadInfoForOrigin = uploadColorMap[origin.upload_id];
          if (uploadInfoForOrigin && typeof uploadInfoForOrigin === 'object' && uploadInfoForOrigin.color) {
            color = String(uploadInfoForOrigin.color);
          }
        }
        return {
          ...origin,
          color: color
        };
      }) : [];
      
      atomicsMap[row.id] = {
        id: row.id,
        upload_ids: uploadIds,
        origins: enrichedOrigins,
        attributes: attrs,
        specificity: row.specificity,
        model: attrs.device_model_name || attrs.user_agent_device_model || 'Unknown Device',
        uploadPlatform: uploadInfo ? uploadInfo.platform : 'Unknown',
        uploadColor: uploadInfo ? uploadInfo.color : '#999999'
      };
    });
  }

  // Return profiles with atomics nested
  return deviceRows.map(row => {
    let attrs = {};
    let origins = [];
    let atomicDeviceIds = [];

    try {
      attrs = row.attributes ? JSON.parse(row.attributes) : {};
      origins = row.origins ? JSON.parse(row.origins) : [];
      atomicDeviceIds = row.atomic_devices_ids ? JSON.parse(row.atomic_devices_ids) : [];
    } catch (e) {
      console.warn('Failed to parse device group', row.id, e);
    }

    const enrichedOrigins = Array.isArray(origins) ? origins.map(origin => {
      if (typeof origin === 'string') {
        return { origin, upload_id: null, color: null };
      }
      let color = null;
      if (origin.upload_id) {
        const uploadInfo = uploadColorMap[origin.upload_id];
        if (uploadInfo && typeof uploadInfo === 'object' && uploadInfo.color) {
          color = String(uploadInfo.color);
        }
      }
      return {
        ...origin,
        color: color
      };
    }) : [];

    return {
      id: row.id,
      atomic_devices_ids: atomicDeviceIds,
      atomicDevices: atomicDeviceIds.map(id => atomicsMap[id] || null).filter(a => a !== null),
      model: row.model || '',
      is_generic: !!row.is_generic,
      user_label: row.user_label,
      notes: row.notes || '',
      origins: enrichedOrigins,
      attributes: attrs,
      os_name: attrs.device_os_name || attrs.user_agent_os_name || attrs.device_os_type || attrs.user_agent_os_type || '',
      os_version: attrs.device_os_version || attrs.user_agent_os_version || '',
      label: row.user_label || row.model || attrs.device_model_name || 'Unknown Device',
      manufacturer: attrs.device_manufacturer || 'TODO: Get from merged attributes',
      city: 'TODO: Calculate from geographic events',
      system_soft_merge: !!row.system_soft_merge
    };
  });
}

