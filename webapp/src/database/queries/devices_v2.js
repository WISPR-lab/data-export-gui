// added for WISPR-lab/data-export-gui
import { getDB } from '../index.js';
import { getUASummary } from './ua_summary.js';
import { hexColor } from '@/utils/hex.js';
import { titleCase } from '@/filters/TitleCase.js';
import { getCondensedModel } from '@/filters/GetCondensedModel.js';
import { getCondensedOS } from '@/filters/GetCondensedOS.js';


export async function getDevices() {
  /* 
   * Queries profiles + instances, parses JSON fields, computes UA summaries and date spans, sorts recognized instances first within each profile.
   *
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

  const profileSql = `SELECT * FROM device_profiles_v2 WHERE deleted = 0`;
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

    inst.upload_color = hexColor(inst.upload_color);

    inst.ua_summary = getUASummary([inst])[0] || null;

    inst.formatted_attributes = formatInstanceAttrs(inst);

    if (!instancesByProfile[inst.device_profile_id]) {
      instancesByProfile[inst.device_profile_id] = [];
    }
    instancesByProfile[inst.device_profile_id].push(inst);
  });

  // sort instances within each profile chronologically, and move recognized ones to top
  Object.values(instancesByProfile).forEach(instances => {
    customSort(instances);
    const recognized = instances.filter(i => i.instance_source_type === 'raw_devices' || i.instance_source_type === 'both');
    const others = instances.filter(i => i.instance_source_type !== 'raw_devices' && i.instance_source_type !== 'both');
    instances.splice(0, instances.length, ...recognized, ...others);
  });

  const mapped = profileRows.map(profile => {
    const profileInstances = instancesByProfile[profile.id] || [];

    // os info from the newest active instance
    const latestOS = (profileInstances[0] && firstInstance.latest_os_version) || '';
    const latestOSName = (profileInstances[0] && firstInstance.os_name) || '';
    const latestOSType = (profileInstances[0] && firstInstance.os_type) || '';

    const allOSVersions = [...new Set(profileInstances.flatMap(inst => inst.os_versions))]; // all unique vals in this profile

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

export async function getInstanceRawAttrs(instanceId) {
  /* Merges deduplicated attributes from all raw device rows linked to this instance, excluding DB-internal keys. */

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

export async function getProfileRawAttrs(profileId) {
  /* Same as getInstanceRawAttrs but joins across all instances under a profile. */
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



function formatInstanceAttrs(inst) {
  /* Builds a display-ready label/value list from instance fields, excluding internal keys; appends timestamp fields at the end. */
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
    'os_versions',
    'apple_masking'
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
  if (osValue && osValue.length > 0) {
    const osLower = String(osValue[0]).toLowerCase();
    if (osLower !== 'unknown' && osLower !== 'null' && osLower !== 'none' && osLower !== 'undefined') {
      attrs.push({ label: 'OS', value: osValue });
    }
  }

  const invalidVals = new Set(['', 'null', 'none', 'unknown', 'undefined']);
  Object.entries(inst).forEach(([key, val]) => {
    if (internalKeys.has(key) || key.includes('latest') || val === undefined || val === null) return;

    let displayValue;
    if (Array.isArray(val)) {
      displayValue = val.map(item => String(item).trim()).filter(item => !invalidVals.has(item.toLowerCase()));
      if (displayValue.length === 0) return;
    } else {
      const displayStr = String(val).trim();
      if (invalidVals.has(displayStr.toLowerCase())) return;
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
      if (aLast === null || aLast === undefined) return 1; 
      if (bLast === null || bLast === undefined) return -1;
      return bLast - aLast; 
    }

    // tie breaker
    const aFirst = a.first_seen;
    const bFirst = b.first_seen;
    if (aFirst !== bFirst) {
      if (aFirst === null || aFirst === undefined) return 1; 
      if (bFirst === null || bFirst === undefined) return -1;
      return bFirst - aFirst; 
    }

    return 0;
  });
}

export async function getProfileNotes(profileId) {
  const db = await getDB();
  const sql = `
    SELECT * FROM device_profile_notes 
    WHERE device_profile_id = ? 
    ORDER BY created_at ASC
  `;
  return await db.exec(sql, {
    bind: [profileId],
    returnValue: 'resultRows',
    rowMode: 'object'
  });
}

export async function addProfileNote(profileId, note) {
  const db = await getDB();
  const id = crypto.randomUUID();
  const ts = Date.now() / 1000;
  const sql = `
    INSERT INTO device_profile_notes (id, device_profile_id, comment, created_at, updated_at) 
    VALUES (?, ?, ?, ?, ?)
  `;
  await db.exec(sql, {
    bind: [id, profileId, note, ts, ts]
  });
  return { id, device_profile_id: profileId, comment: note, created_at: ts, updated_at: ts };
}
