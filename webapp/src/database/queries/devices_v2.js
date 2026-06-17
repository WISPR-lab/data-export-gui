// added for WISPR-lab/data-export-gui
import { getDB } from '../index.js';
import { getUASummary } from './ua_summary.js';
import { hexColor } from '@/utils/hex.js';
import { titleCase } from '@/filters/TitleCase.js';

export async function getDevices() {
  /*
   * Example return value format with dummy data:
   * [
   *   {
   *     id: "33595835-fd99-4bee-8f2d-6fa7b83d23f0",
   *     model: "iPhone 11 Pro Max",
   *     manufacturer: "apple",
   *     os_type: "ios",
   *     user_label: "My Personal Phone",
   *     notes: "Primary test device.",
   *     label: "My Personal Phone",
   *     first_seen: 1769022758,
   *     last_seen: 1779298838,
   *     latest_os_version: "26.3.1",
   *     latest_os_name: "iOS",
   *     latest_os_type: "ios",
   *     instance_count: 1,
   *     all_os_versions: ["26.3.1"],
   *     ua_summaries: [
   *       { primary: "Instagram App", secondary: "WebKit", color: "#97D788" }
   *     ],
   *     instances: [
   *       {
   *         id: "89fd6bb9-b0bd-4be3-bc49-2ef5d5a3fd66",
   *         upload_id: "6fff6a23-379f-45fd-9038-7376831ce6f7",
   *         platform: "instagram",
   *         model: "iPhone 11 Pro Max",
   *         os_name: "iOS",
   *         first_seen: 1769022758,
   *         last_seen: 1779298838,
   *         upload_color: "#97D788",
   *         os_versions: ["26.3.1"],
   *         formatted_attributes: [
   *           { label: "Model", value: "iPhone 11 Pro Max" }
   *         ]
   *       }
   *     ]
   *   }
   * ]
   */
  const db = await getDB();

  const profileSql = `SELECT * FROM device_profiles_v2`;
  const profileRows = await db.exec(profileSql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });

  const instanceSql = `
    SELECT 
      di.*, 
      dpi.device_profile_id,
      u.color as upload_color,
      CASE 
        WHEN EXISTS (
          SELECT 1 FROM device_instance_raw_devices dir 
          WHERE dir.device_instance_id = di.id
        ) AND EXISTS (
          SELECT 1 FROM device_instance_events die 
          WHERE die.device_instance_id = di.id
        ) THEN 'both'
        WHEN EXISTS (
          SELECT 1 FROM device_instance_raw_devices dir 
          WHERE dir.device_instance_id = di.id
        ) THEN 'raw_devices'
        WHEN EXISTS (
          SELECT 1 FROM device_instance_events die 
          WHERE die.device_instance_id = di.id
        ) THEN 'events'
        ELSE 'unknown'
      END AS instance_source_type
    FROM device_instances di
    JOIN device_profile_instances dpi ON di.id = dpi.device_instance_id
    LEFT JOIN uploads u ON di.upload_id = u.id
  `;
  const instanceRows = await db.exec(instanceSql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });

  // Group instances by their profile ID
  const instancesByProfile = {};
  instanceRows.forEach(inst => {
    const parseField = (fieldVal) => {
      if (!fieldVal) return [];
      try {
        const parsed = typeof fieldVal === 'string' ? JSON.parse(fieldVal) : fieldVal;
        return Array.isArray(parsed) ? parsed : [];
      } catch (e) {
        console.warn('Failed to parse field', fieldVal, e);
        return [];
      }
    };

    inst.os_versions = parseField(inst.os_versions);
    inst.client_versions = parseField(inst.client_versions);
    inst.client_ips = parseField(inst.client_ips);
    inst.locations = parseField(inst.locations);

    // normalize upload_color to a full hex string
    inst.upload_color = hexColor(inst.upload_color);

    // Attach user agent summary classification to the individual instance
    inst.ua_summary = getUASummary([inst])[0] || null;

    inst.formatted_attributes = formatInstanceAttrs(inst);

    if (!instancesByProfile[inst.device_profile_id]) {
      instancesByProfile[inst.device_profile_id] = [];
    }
    instancesByProfile[inst.device_profile_id].push(inst);
  });

  // Sort instances within each profile chronologically, and move recognized ones to top
  Object.values(instancesByProfile).forEach(instances => {
    customSort(instances);
    const recognized = instances.filter(i => i.instance_source_type === 'raw_devices' || i.instance_source_type === 'both');
    const others = instances.filter(i => i.instance_source_type !== 'raw_devices' && i.instance_source_type !== 'both');
    instances.splice(0, instances.length, ...recognized, ...others);
  });

  const mapped = profileRows.map(profile => {
    const profileInstances = instancesByProfile[profile.id] || [];

    // os info from the newest active instance
    const firstInstance = profileInstances[0];
    const latestOS = (firstInstance && firstInstance.latest_os_version) || '';
    const latestOSName = (firstInstance && firstInstance.os_name) || '';
    const latestOSType = (firstInstance && firstInstance.os_type) || '';

    // Collect all unique OS versions in this profile
    const allOSVersions = [...new Set(profileInstances.flatMap(inst => inst.os_versions))];

    // Compute safe, finite timeline boundaries (or null if empty/invalid)
    const validFirstSeens = profileInstances.map(i => i.first_seen).filter(ts => typeof ts === 'number' && !isNaN(ts));
    const validLastSeens = profileInstances.map(i => i.last_seen).filter(ts => typeof ts === 'number' && !isNaN(ts));

    return {
      id: profile.id,
      model: profile.model || '',
      manufacturer: profile.manufacturer || '',
      os_type: profile.os_type || '',
      user_label: profile.user_label,
      notes: profile.notes || '',
      label: profile.user_label || profile.model || 'Unknown Device',
      
      // list of session/app instances grouped under this profile
      instances: profileInstances,
      ua_summaries: getUASummary(profileInstances),
      all_os_versions: allOSVersions,
      
      // active date span (min/max timestamps)
      first_seen: validFirstSeens.length ? Math.min(...validFirstSeens) : null,
      last_seen: validLastSeens.length ? Math.max(...validLastSeens) : null,
      
      // quick summary details for ui headers
      latest_os_version: latestOS,
      latest_os_name: latestOSName,
      latest_os_type: latestOSType,
      instance_count: profileInstances.length
    };
  });

  return customSort(mapped);
}

// update editable fields (user_label, notes) of a device profile
export async function updateProfile(profileId, updates) {
  const db = await getDB();
  
  const allowed = ['user_label', 'notes'];
  const keys = Object.keys(updates).filter(k => allowed.includes(k));
  if (keys.length === 0) return;
  
  const setClause = keys.map(k => `${k} = ?`).join(', ');
  const params = [...keys.map(k => updates[k]), profileId];
  
  const sql = `UPDATE device_profiles_v2 SET ${setClause}, updated_at = ? WHERE id = ?`;
  params.splice(params.length - 1, 0, Date.now() / 1000);

  await db.exec(sql, { bind: params });
}

/**
 * Fetches all associated devices_raw rows for the instance, parses their JSON attributes,
 * filters out database-specific noise (like id and upload_id), and compiles a de-duplicated
 * key-value list of all unique attributes to display.
 */
export async function getInstanceRawAttrs(instanceId) {
  const db = await getDB();
  const sql = `
    SELECT dr.attributes 
    FROM devices_raw dr
    JOIN device_instance_raw_devices dird ON dr.id = dird.devices_raw_id
    WHERE dird.device_instance_id = ?
  `;
  const rows = await db.exec(sql, {
    bind: [instanceId],
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  const mergedAttributes = {};
  rows.forEach(row => {
    try {
      const attrs = row.attributes ? JSON.parse(row.attributes) : {};
      Object.entries(attrs).forEach(([key, val]) => {
        if (['id', 'upload_id', 'file_id', 'raw_data_id'].includes(key)) {
          return;
        }
        if (val !== null && val !== undefined && val !== '') {
          mergedAttributes[key] = val;
        }
      });
    } catch (e) {
      console.warn('Failed to parse raw device attributes', e);
    }
  });
  
  return mergedAttributes;
}

// fetch all raw devices_raw attributes for all instances under a profile
export async function getProfileRawAttrs(profileId) {
  const db = await getDB();
  const sql = `
    SELECT dr.attributes 
    FROM devices_raw dr
    JOIN device_instance_raw_devices dird ON dr.id = dird.devices_raw_id
    JOIN device_profile_instances dpi ON dird.device_instance_id = dpi.device_instance_id
    WHERE dpi.device_profile_id = ?
  `;
  const rows = await db.exec(sql, {
    bind: [profileId],
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  const mergedAttributes = {};
  rows.forEach(row => {
    try {
      const attrs = row.attributes ? JSON.parse(row.attributes) : {};
      Object.entries(attrs).forEach(([key, val]) => {
        if (['id', 'upload_id', 'file_id', 'raw_data_id'].includes(key)) {
          return;
        }
        if (val !== null && val !== undefined && val !== '') {
          mergedAttributes[key] = val;
        }
      });
    } catch (e) {
      console.warn('Failed to parse raw device attributes', e);
    }
  });
  
  return mergedAttributes;
}

export function getCondensedModel(manufacturer, model) {
  const mfr = (manufacturer || '').trim();
  const mdl = (model || '').trim();
  if (mfr && mdl) {
    if (mdl.toLowerCase().startsWith(mfr.toLowerCase())) {
      return mdl;
    }
    return `${mfr} ${mdl}`;
  }
  return mdl || mfr || '';
}

export function getCondensedOS(osName, versions) {
  const name = osName || '';
  const list = (versions || []).filter(Boolean);
  if (!name) return '';
  const titleName = titleCase(name);
  if (list.length > 0) {
    const listCopy = [...list];
    listCopy.sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));
    const firstV = listCopy[0];
    const lastV = listCopy[listCopy.length - 1];
    if (firstV === lastV) {
      return `${titleName} ${firstV}`;
    }
    return `${titleName} ${firstV} → ${lastV}`;
  }
  return titleName;
}

function formatInstanceAttrs(inst) {
  const internalKeys = new Set([
    'id', 
    'upload_id', 
    'device_profile_id',
    'upload_color',
    'created_at', 
    'event_count', 
    'first_seen', 
    'last_seen', 
    'last_seen_dt', 
    'ua_summary', 
    'instance_source_type',
    'latest_os_version',
    'platform',
    'manufacturer',
    'model',
    'os_name',
    'os_type',
    'os_versions'
  ]);

  const keyLabel = (str) => {
    if (str === 'client_ips' || str === 'client_ip') return 'IP Addresses';
    return str
      .split('_')
      .map(word => titleCase(word))
      .join(' ');
  };

  const attrs = [];

  if (inst.id) {
    attrs.push({ label: 'Instance ID', value: inst.id });
  }

  // Condense Manufacturer and Model into a single 'Model' value
  const modelValue = getCondensedModel(inst.manufacturer, inst.model);
  const modelLower = modelValue.toLowerCase();
  if (modelValue && modelLower !== 'unknown' && modelLower !== 'null' && modelLower !== 'none' && modelLower !== 'undefined') {
    attrs.push({ label: 'Model', value: modelValue });
  }

  // Construct OS field
  const osValue = getCondensedOS(inst.os_name || inst.os_type, inst.os_versions);
  const osLower = osValue.toLowerCase();
  if (osValue && osLower !== 'unknown' && osLower !== 'null' && osLower !== 'none' && osLower !== 'undefined') {
    attrs.push({ label: 'OS', value: osValue });
  }

  Object.entries(inst).forEach(([key, val]) => {
    if (internalKeys.has(key)) return;
    if (key.includes('latest')) return;
    if (val === undefined || val === null) return;
    if (Array.isArray(val) && val.length === 0) return;

    let displayValue = val;
    if (Array.isArray(val)) {
      displayValue = val.map(function (item) { return String(item).trim(); }).filter(function (item) {
        const lower = item.toLowerCase();
        return item !== '' && lower !== 'null' && lower !== 'none' && lower !== 'unknown' && lower !== 'undefined';
      });
      if (displayValue.length === 0) return;
    } else {
      const displayStr = String(val).trim();
      const lower = displayStr.toLowerCase();
      if (!displayStr || lower === 'null' || lower === 'none' || lower === 'unknown' || lower === 'undefined') {
        return;
      }
      displayValue = displayStr;
    }

    attrs.push({
      label: keyLabel(key),
      value: displayValue
    });
  });

  if (inst.first_seen) {
    attrs.push({ label: 'First Active', value: inst.first_seen, isTimestamp: true });
  }

  if (inst.last_seen && inst.last_seen !== inst.first_seen) {
    attrs.push({ label: 'Last Active', value: inst.last_seen, isTimestamp: true });
  }

  return attrs;
}

// sort items in-place (newest active to oldest)
export function customSort(items) {
  if (!Array.isArray(items)) return [];
  return items.sort((a, b) => {
    const aLast = a.last_seen;
    const bLast = b.last_seen;
    if (aLast !== bLast) {
      if (aLast === null || aLast === undefined) return 1;  // push nulls to the bottom
      if (bLast === null || bLast === undefined) return -1;
      return bLast - aLast; // Newest first
    }

    // tie breaker
    const aFirst = a.first_seen;
    const bFirst = b.first_seen;
    if (aFirst !== bFirst) {
      if (aFirst === null || aFirst === undefined) return 1;  // push nulls to the bottom
      if (bFirst === null || bFirst === undefined) return -1;
      return bFirst - aFirst; // Newest first
    }

    return 0;
  });
}

function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export async function getProfileComments(profileId) {
  const db = await getDB();
  const sql = `
    SELECT * FROM device_profile_comments 
    WHERE device_profile_id = ? 
    ORDER BY created_at ASC
  `;
  return await db.exec(sql, {
    bind: [profileId],
    returnValue: 'resultRows',
    rowMode: 'object'
  });
}

export async function addProfileComment(profileId, comment) {
  const db = await getDB();
  const id = generateUUID();
  const ts = Date.now() / 1000;
  const sql = `
    INSERT INTO device_profile_comments (id, device_profile_id, comment, created_at, updated_at) 
    VALUES (?, ?, ?, ?, ?)
  `;
  await db.exec(sql, {
    bind: [id, profileId, comment, ts, ts]
  });
  return { id, device_profile_id: profileId, comment, created_at: ts, updated_at: ts };
}

export async function getUserDeviceEdits() {
  const db = await getDB();
  await db.exec(`
    CREATE TABLE IF NOT EXISTS user_device_edits (
      id TEXT PRIMARY KEY,
      action_type TEXT,
      instance_ids JSONTEXT,
      instance_summaries JSONTEXT,
      source_profile_id TEXT,
      target_profile_id TEXT,
      source_profile_label TEXT,
      target_profile_label TEXT,
      reason TEXT,
      created_at REAL
    )
  `);

  const sql = `SELECT * FROM user_device_edits ORDER BY created_at DESC`;
  const rows = await db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });

  return rows.map(function(row) {
    try {
      row.instance_ids = row.instance_ids ? JSON.parse(row.instance_ids) : [];
    } catch (e) {
      row.instance_ids = [];
    }
    try {
      row.instance_summaries = row.instance_summaries ? JSON.parse(row.instance_summaries) : [];
    } catch (e) {
      row.instance_summaries = [];
    }
    return row;
  });
}

export async function createUserDeviceEdit(params) {
  const db = await getDB();
  await db.exec(`
    CREATE TABLE IF NOT EXISTS user_device_edits (
      id TEXT PRIMARY KEY,
      action_type TEXT,
      instance_ids JSONTEXT,
      instance_summaries JSONTEXT,
      source_profile_id TEXT,
      target_profile_id TEXT,
      source_profile_label TEXT,
      target_profile_label TEXT,
      reason TEXT,
      created_at REAL
    )
  `);

  const id = generateUUID();
  const ts = Date.now() / 1000;
  const sql = `
    INSERT INTO user_device_edits 
    (id, action_type, instance_ids, instance_summaries, source_profile_id, target_profile_id, source_profile_label, target_profile_label, reason, created_at) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `;
  await db.exec(sql, {
    bind: [
      id,
      params.action_type,
      JSON.stringify(params.instance_ids || []),
      JSON.stringify(params.instance_summaries || []),
      params.source_profile_id || null,
      params.target_profile_id || null,
      params.source_profile_label || null,
      params.target_profile_label || null,
      params.reason || '',
      ts
    ]
  });
  return {
    id,
    action_type: params.action_type,
    instance_ids: params.instance_ids,
    instance_summaries: params.instance_summaries,
    source_profile_id: params.source_profile_id,
    target_profile_id: params.target_profile_id,
    source_profile_label: params.source_profile_label,
    target_profile_label: params.target_profile_label,
    reason: params.reason,
    created_at: ts
  };
}


