import { getDB } from '../index.js';
import { getUASummary } from './ua_summary.js';

/**
 * @returns {Promise<Array<Object>>} List of device profiles. Each profile matches the following shape:
 * {
 *   id: String (UUID),
 *   model: String (e.g. "iPhone 13"),
 *   manufacturer: String (e.g. "Apple"),
 *   user_label: String | null (e.g. "Work Phone"),
 *   notes: String,
 *   label: String (user_label || model),
 *   instance_count: Number,
 *   latest_os_version: String (e.g. "17.1" - shortcut OS version from most recently active instance),
 *   latest_os_name: String (e.g. "ios" - normalized lowercase OS name from most recently active instance),
 *   latest_os_type: String (e.g. "ios" - normalized lowercase OS type from most recently active instance),
 *   first_seen: Number | null (min timestamp in seconds across all child instances),
 *   last_seen: Number | null (max timestamp in seconds across all child instances),
 *   all_os_versions: Array<String> (unique clean version strings, e.g. ["16.5", "17.1"]),
 *   ua_summaries: Array<{
 *     primary: String (e.g. "Gmail App"),
 *     secondary: String (e.g. "Safari WebView" or ""),
 *     color: String (HEX color, e.g. "#4285F4")
 *   }> (de-duplicated across all child instances; each entry can be rendered as "Primary (Secondary)"),
 *   instances: Array<Object> (list of associated DeviceInstance records, see getDeviceInstances schema)
 * }
 */
export async function getDevices() {
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
      COALESCE(u.color, '5E75C2') as upload_color,
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
    try {
      inst.os_versions = inst.os_versions ? JSON.parse(inst.os_versions) : [];
      inst.client_versions = inst.client_versions ? JSON.parse(inst.client_versions) : [];
      inst.ip_addresses = inst.ip_addresses ? JSON.parse(inst.ip_addresses) : [];
      inst.locations = inst.locations ? JSON.parse(inst.locations) : [];
    } catch (e) {
      console.warn('Failed to parse attributes for device instance', inst.id, e);
      inst.os_versions = inst.os_versions || [];
      inst.client_versions = inst.client_versions || [];
      inst.ip_addresses = inst.ip_addresses || [];
      inst.locations = inst.locations || [];
    }

    // Normalize upload_color to a full hex string (DB stores it without the leading '#')
    let color = inst.upload_color ? String(inst.upload_color) : '#5E75C2';
    if (color.length > 0 && color[0] !== '#') color = '#' + color;
    inst.upload_color = color;

    // Attach user agent summary classification to the individual instance
    // Returns a single summary dict (or null) rather than an array
    inst.ua_summary = getUASummary([inst])[0] || null;

    inst.formatted_attributes = computeFormattedAttributes(inst);

    if (!instancesByProfile[inst.device_profile_id]) {
      instancesByProfile[inst.device_profile_id] = [];
    }
    instancesByProfile[inst.device_profile_id].push(inst);
  });

  return profileRows.map(profile => {
    const profileInstances = instancesByProfile[profile.id] || [];

    // let "latest" os from from the most recently active instance
    const sortedInstances = [...profileInstances].sort((a, b) => (b.last_seen || 0) - (a.last_seen || 0));
    const firstInstance = sortedInstances[0];
    const latestOS = (firstInstance && firstInstance.latest_os_version) || '';
    const latestOSName = (firstInstance && firstInstance.os_name) || '';
    const latestOSType = (firstInstance && firstInstance.os_type) || '';

    // Collect all unique OS versions in this profile
    const allOSVersions = [...new Set(profileInstances.flatMap(inst => inst.os_versions))];

    return {
      id: profile.id,
      model: profile.model || '',
      manufacturer: profile.manufacturer || '',
      os_type: profile.os_type || '',
      user_label: profile.user_label,
      notes: profile.notes || '',
      label: profile.user_label || profile.model || 'Unknown Device',
      
      // Nest child instances
      instances: profileInstances,

      // De-duplicated UA summaries across all child instances.
      // Each entry: { primary, secondary, color } — renderable as "Primary (Secondary)".
      ua_summaries: getUASummary(profileInstances),
      all_os_versions: allOSVersions,
      
      // Timeline boundaries
      first_seen: profileInstances.length ? Math.min(...profileInstances.map(i => i.first_seen || Infinity)) : null,
      last_seen: profileInstances.length ? Math.max(...profileInstances.map(i => i.last_seen || -Infinity)) : null,
      
      // Shortcut metrics
      latest_os_version: latestOS,
      latest_os_name: latestOSName,
      latest_os_type: latestOSType,
      instance_count: profileInstances.length
    };
  });
}

/**
 * Fetches a list of specific device instances by their IDs, with upload colors.
 *
 * @param {Array<String>} instanceIds List of instance IDs.
 * @returns {Promise<Array<Object>>} List of hydrated device instances matching the shape:
 * {
 *   id: String (UUID),
 *   upload_id: String (upload provenance),
 *   platform: String (lowercase, e.g. "google"),
 *   manufacturer: String,
 *   model: String,
 *   client_name: String (raw composite, e.g. "Chrome :: WebView"),
 *   os_name: String (lowercase, e.g. "ios"),
 *   os_type: String (lowercase, e.g. "ios"),
 *   apple_masking: String,
 *   first_seen: Number (timestamp in seconds),
 *   last_seen: Number (timestamp in seconds),
 *   event_count: Number,
 *   latest_os_version: String (e.g. "17.0.1"),
 *   latest_client_version: String,
 *   latest_ip_address: String,
 *   os_versions: Array<String> (e.g. ["16.5", "17.0.1"]),
 *   client_versions: Array<String>,
 *   ip_addresses: Array<String>,
 *   locations: Array<String>,
 *   upload_color: String (HEX color of upload provenance),
 *   ua_summary: { primary: String, secondary: String, color: String } | null
 * }
 */
export async function getDeviceInstances(instanceIds) {
  const db = await getDB();
  if (!instanceIds || instanceIds.length === 0) return [];

  const placeholders = instanceIds.map(() => '?').join(',');
  const sql = `
    SELECT 
      di.*, 
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
    LEFT JOIN uploads u ON di.upload_id = u.id
    WHERE di.id IN (${placeholders})
  `;

  const rows = await db.exec(sql, {
    bind: instanceIds,
    returnValue: 'resultRows',
    rowMode: 'object'
  });

  return rows.map(inst => {
    try {
      inst.os_versions = inst.os_versions ? JSON.parse(inst.os_versions) : [];
      inst.client_versions = inst.client_versions ? JSON.parse(inst.client_versions) : [];
      inst.ip_addresses = inst.ip_addresses ? JSON.parse(inst.ip_addresses) : [];
      inst.locations = inst.locations ? JSON.parse(inst.locations) : [];
    } catch (e) {
      console.warn('Failed to parse JSON columns for instance', inst.id, e);
    }

    let color = inst.upload_color ? String(inst.upload_color) : '#999999';
    if (color.length > 0 && color[0] !== '#') {
      color = '#' + color;
    }
    inst.upload_color = color;

    inst.ua_summary = getUASummary([inst])[0] || null;

    inst.formatted_attributes = computeFormattedAttributes(inst);

    return inst;
  });
}

/**
 * Updates editable fields (user_label, notes) of a device profile.
 */
export async function updateDeviceProfile(profileId, updates) {
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
export async function getInstanceAttributes(instanceId) {
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

/**
 * Fetches all associated devices_raw attributes for all instances under a given profile.
 */
export async function getProfileAttributes(profileId) {
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

function computeFormattedAttributes(inst) {
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
    'latest_os_version'
  ]);

  const titleCase = (str) => {
    return str
      .split('_')
      .map(word => {
        const lower = word.toLowerCase();
        if (lower === 'os') return 'OS';
        if (lower === 'ip') return 'IP';
        return word.charAt(0).toUpperCase() + word.slice(1);
      })
      .join(' ');
  };

  const formatDate = (ts) => {
    if (!ts) return null;
    return new Date(ts * 1000).toLocaleDateString(undefined, { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric' 
    });
  };

  const attrs = [];

  // 1. Process standard fields
  Object.entries(inst).forEach(([key, val]) => {
    if (internalKeys.has(key)) return;
    if (key.includes('latest')) return;
    if (val === undefined || val === null) return;
    if (Array.isArray(val) && val.length === 0) return;
    if (typeof val === 'string' && !val.trim()) return;

    let displayValue = val;
    if (Array.isArray(val)) {
      displayValue = val.join(', ');
    } else if (typeof val === 'string') {
      displayValue = val.trim();
    }

    attrs.push({
      label: titleCase(key),
      value: String(displayValue)
    });
  });

  // 2. Add First Seen & Last Seen based on availability and logic
  const firstSeenStr = formatDate(inst.first_seen);
  const lastSeenStr = formatDate(inst.last_seen);

  if (firstSeenStr) {
    attrs.push({ label: 'First Seen', value: firstSeenStr });
  }

  // Only show Last Seen if it is present and different from First Seen, or if it represents a session range
  if (lastSeenStr && lastSeenStr !== firstSeenStr) {
    attrs.push({ label: 'Last Seen', value: lastSeenStr });
  }

  return attrs;
}

