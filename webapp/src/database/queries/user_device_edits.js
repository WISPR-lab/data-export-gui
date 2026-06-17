// custom to WISPR-lab/data-export-gui
import { getDB } from '../index.js';

function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

async function getProfileLabel(db, profileId) {
  if (!profileId) return '';
  const sql = 'SELECT user_label, model FROM device_profiles_v2 WHERE id = ?';
  const rows = await db.exec(sql, { bind: [profileId], returnValue: 'resultRows', rowMode: 'object' });
  const row = rows && rows[0];
  if (row) {
    return row.user_label || row.model || 'Unknown Profile';
  }
  return '';
}

async function getInstanceSummaries(db, instanceIds) {
  const placeholders = instanceIds.map(function() { return '?'; }).join(',');
  const sql = `SELECT id, platform, client_name, os_name, os_type, first_seen FROM device_instances WHERE id IN (${placeholders})`;
  const rows = await db.exec(sql, {
    bind: instanceIds,
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  
  const summaries = [];
  instanceIds.forEach(function(id) {
    const found = rows ? rows.find(function(r) { return r.id === id; }) : null;
    if (found) {
      const appName = found.client_name || 'Session';
      const os = found.os_name || found.os_type || 'Unknown OS';
      const dates = found.first_seen ? new Date(found.first_seen * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '';
      let text = appName + ' on ' + os;
      if (dates) text += ' (Active: ' + dates + ')';
      text += ' [ID: ' + id.substring(0, 4) + '...]';
      summaries.push(text);
    } else {
      summaries.push('Session [ID: ' + id.substring(0, 4) + '...]');
    }
  });
  return summaries;
}

export async function getUserDeviceEdits() {
  const db = await getDB();
  const sql = 'SELECT * FROM user_device_edits ORDER BY created_at DESC';
  const rows = await db.exec(sql, {
    returnValue: 'resultRows',
    rowMode: 'object'
  });

  return (rows || []).map(function(row) {
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

export async function addUserDeviceEdit(params) {
  const db = await getDB();
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
    id: id,
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

export function checkMoveEligibility(targetProfile, selectedInstances) {
  if (!targetProfile || !selectedInstances || selectedInstances.length === 0) {
    return { isEligible: false, reason: 'No destination or selection' };
  }

  const targetOS = (targetProfile.os_type || '').trim().toLowerCase();
  const targetMfr = (targetProfile.manufacturer || '').trim().toLowerCase();
  const targetModel = (targetProfile.model || '').trim().toLowerCase();

  for (let i = 0; i < selectedInstances.length; i++) {
    const inst = selectedInstances[i];
    const instOS = (inst.os_type || inst.os_name || '').trim().toLowerCase();
    const instMfr = (inst.manufacturer || '').trim().toLowerCase();
    const instModel = (inst.model || '').trim().toLowerCase();

    // 1. OS Check: Cannot cross OS lines if both are specific (e.g. android and ios)
    if (targetOS && instOS && targetOS !== instOS) {
      if (
        (targetOS === 'android' || targetOS === 'ios') &&
        (instOS === 'android' || instOS === 'ios')
      ) {
        return { isEligible: false, reason: 'Mismatched OS: ' + targetProfile.os_type + ' and ' + (inst.os_type || inst.os_name) };
      }
    }

    // 2. Manufacturer Check: Cannot merge different specific manufacturers (e.g. apple and google)
    if (targetMfr && instMfr && targetMfr !== instMfr) {
      if (
        targetMfr !== 'unknown' && targetMfr !== 'null' && targetMfr !== 'none' &&
        instMfr !== 'unknown' && instMfr !== 'null' && instMfr !== 'none'
      ) {
        return { isEligible: false, reason: 'Mismatched Manufacturer: ' + targetProfile.manufacturer + ' and ' + inst.manufacturer };
      }
    }

    // 3. Model Check: Cannot merge different specific hardware models (e.g. iphone 11 and iphone 7)
    if (targetModel && instModel && targetModel !== instModel) {
      const isTargetGeneric = targetModel === 'iphone' || targetModel === 'macintosh' || targetModel === 'android';
      const isInstGeneric = instModel === 'iphone' || instModel === 'macintosh' || instModel === 'android';

      if (!isTargetGeneric && !isInstGeneric) {
        return { isEligible: false, reason: 'Mismatched Models: ' + targetProfile.model + ' and ' + inst.model };
      }
    }
  }

  return { isEligible: true, reason: '' };
}

export function resolveProfileAttributes(instances) {
  if (!instances || instances.length === 0) {
    return { manufacturer: null, model: null, os_type: null };
  }

  function scoreValue(val) {
    if (!val) return -1;
    const s = String(val).trim().toLowerCase();
    if (s === '' || s === 'unknown' || s === 'null' || s === 'none' || s === 'undefined') {
      return -1;
    }
    return s.length;
  }

  // Sort by recency (newest last_seen first)
  const sortedByRecency = [...instances].sort(function(a, b) {
    return (b.last_seen || 0) - (a.last_seen || 0);
  });

  // OS (Recency matches best)
  let os = null;
  for (let i = 0; i < sortedByRecency.length; i++) {
    const val = sortedByRecency[i].os_type || sortedByRecency[i].os_name;
    if (scoreValue(val) > 0) {
      os = val;
      break;
    }
  }

  // Manufacturer (Recency first)
  let mfr = null;
  for (let i = 0; i < sortedByRecency.length; i++) {
    const val = sortedByRecency[i].manufacturer;
    if (scoreValue(val) > 0) {
      mfr = val;
      break;
    }
  }

  // Model (Prioritize specificity/length, break ties with recency)
  let model = null;
  const candidates = [];
  for (let i = 0; i < instances.length; i++) {
    const val = instances[i].model;
    if (scoreValue(val) > 0) {
      candidates.push({
        value: val,
        recency: instances[i].last_seen || 0,
        score: scoreValue(val)
      });
    }
  }

  if (candidates.length > 0) {
    candidates.sort(function(a, b) {
      if (a.score !== b.score) {
        return b.score - a.score; // Higher score (longer string) first
      }
      return b.recency - a.recency; // Newer first
    });
    model = candidates[0].value;
  }

  return {
    manufacturer: mfr,
    model: model,
    os_type: os
  };
}

async function updateProfileAttributes(db, profileId) {
  // Query all instances currently mapped to this profile
  const sql = `
    SELECT di.manufacturer, di.model, di.os_type, di.os_name, di.last_seen
    FROM device_instances di
    JOIN device_profile_instances dpi ON di.id = dpi.device_instance_id
    WHERE dpi.device_profile_id = ?
  `;
  const rows = await db.exec(sql, {
    bind: [profileId],
    returnValue: 'resultRows',
    rowMode: 'object'
  });

  if (!rows || rows.length === 0) return;

  const resolved = resolveProfileAttributes(rows);
  const now = Date.now() / 1000;

  const updateSql = `
    UPDATE device_profiles_v2
    SET manufacturer = ?, model = ?, os_type = ?, updated_at = ?
    WHERE id = ?
  `;
  await db.exec(updateSql, {
    bind: [resolved.manufacturer, resolved.model, resolved.os_type, now, profileId]
  });
}

export async function moveInstancesToProfile(instanceIds, targetProfileId, reason) {
  const db = await getDB();

  // Find source profiles of these instances before we move them
  const placeholders = instanceIds.map(function() { return '?'; }).join(',');
  const findSql = `SELECT DISTINCT device_profile_id FROM device_profile_instances WHERE device_instance_id IN (${placeholders})`;
  const sourceRows = await db.exec(findSql, {
    bind: instanceIds,
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  const sourceProfileIds = (sourceRows || [])
    .map(function(r) { return r.device_profile_id; })
    .filter(function(id) { return id !== targetProfileId; });

  const sourceProfileId = sourceProfileIds[0] || null;
  const sourceProfileLabel = await getProfileLabel(db, sourceProfileId);
  const targetProfileLabel = await getProfileLabel(db, targetProfileId);
  const instanceSummaries = await getInstanceSummaries(db, instanceIds);

  // Map instances to target profile
  for (let i = 0; i < instanceIds.length; i++) {
    const instId = instanceIds[i];
    await db.exec('DELETE FROM device_profile_instances WHERE device_instance_id = ?', { bind: [instId] });
    await db.exec('INSERT INTO device_profile_instances (device_profile_id, device_instance_id) VALUES (?, ?)', {
      bind: [targetProfileId, instId]
    });
  }

  // Update target profile metadata
  await updateProfileAttributes(db, targetProfileId);

  // Find profiles that will be empty before marking them deleted
  const emptyRows = await db.exec(`
    SELECT id, user_label, model FROM device_profiles_v2
    WHERE deleted = 0 AND id NOT IN (SELECT DISTINCT device_profile_id FROM device_profile_instances)
  `, { returnValue: 'resultRows', rowMode: 'object' });

  // Prune empty profiles
  await db.exec(`
    UPDATE device_profiles_v2
    SET deleted = 1
    WHERE id NOT IN (SELECT DISTINCT device_profile_id FROM device_profile_instances)
  `);

  if (emptyRows && emptyRows.length > 0) {
    for (let i = 0; i < emptyRows.length; i++) {
      const p = emptyRows[i];
      const pLabel = p.user_label || p.model || 'Unknown Profile';
      await addUserDeviceEdit({
        action_type: 'delete_profile',
        instance_ids: [],
        instance_summaries: [],
        source_profile_id: p.id,
        target_profile_id: null,
        source_profile_label: pLabel,
        target_profile_label: null,
        reason: 'Profile became empty and was deleted'
      });
    }
  }

  // Update attributes of remaining source profiles (if they were not pruned)
  for (let i = 0; i < sourceProfileIds.length; i++) {
    const srcId = sourceProfileIds[i];
    const checkSql = 'SELECT COUNT(*) as cnt FROM device_profiles_v2 WHERE id = ?';
    const checkRow = await db.exec(checkSql, { bind: [srcId], returnValue: 'resultRows', rowMode: 'object' });
    if (checkRow && checkRow[0] && checkRow[0].cnt > 0) {
      await updateProfileAttributes(db, srcId);
    }
  }

  // Log move to user_device_edits ledger table
  await addUserDeviceEdit({
    action_type: 'move_instances',
    instance_ids: instanceIds,
    instance_summaries: instanceSummaries,
    source_profile_id: sourceProfileId,
    target_profile_id: targetProfileId,
    source_profile_label: sourceProfileLabel,
    target_profile_label: targetProfileLabel,
    reason: reason
  });

  return { status: 'ok', message: 'Moved instances successfully' };
}

export async function createProfileWithInstances(instanceIds, newProfileLabel, reason) {
  const db = await getDB();
  
  if (!instanceIds || instanceIds.length === 0) {
    throw new Error('No instances specified to create profile');
  }

  // Get metadata from the first instance
  const sql = 'SELECT manufacturer, model, os_type, os_name, last_seen FROM device_instances WHERE id = ?';
  const instRows = await db.exec(sql, {
    bind: [instanceIds[0]],
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  const firstInst = instRows && instRows[0];

  // Find source profiles of these instances before we move them
  const placeholders = instanceIds.map(function() { return '?'; }).join(',');
  const findSql = `SELECT DISTINCT device_profile_id FROM device_profile_instances WHERE device_instance_id IN (${placeholders})`;
  const sourceRows = await db.exec(findSql, {
    bind: instanceIds,
    returnValue: 'resultRows',
    rowMode: 'object'
  });
  const sourceProfileIds = (sourceRows || [])
    .map(function(r) { return r.device_profile_id; });

  const sourceProfileId = sourceProfileIds[0] || null;
  const sourceProfileLabel = await getProfileLabel(db, sourceProfileId);
  const instanceSummaries = await getInstanceSummaries(db, instanceIds);

  const newProfileId = generateUUID();
  const now = Date.now() / 1000;

  // Insert the new profile (user_created = 1)
  const insertSql = `
    INSERT INTO device_profiles_v2 (id, manufacturer, model, os_type, user_label, notes, user_created, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `;
  await db.exec(insertSql, {
    bind: [
      newProfileId,
      (firstInst && firstInst.manufacturer) || null,
      (firstInst && firstInst.model) || null,
      (firstInst && (firstInst.os_type || firstInst.os_name)) || null,
      newProfileLabel,
      '',
      1,
      now,
      now
    ]
  });

  // Map instances to new profile
  for (let i = 0; i < instanceIds.length; i++) {
    const instId = instanceIds[i];
    await db.exec('DELETE FROM device_profile_instances WHERE device_instance_id = ?', { bind: [instId] });
    await db.exec('INSERT INTO device_profile_instances (device_profile_id, device_instance_id) VALUES (?, ?)', {
      bind: [newProfileId, instId]
    });
  }

  // Find profiles that will be empty before marking them deleted
  const emptyRows = await db.exec(`
    SELECT id, user_label, model FROM device_profiles_v2
    WHERE deleted = 0 AND id NOT IN (SELECT DISTINCT device_profile_id FROM device_profile_instances)
  `, { returnValue: 'resultRows', rowMode: 'object' });

  // Prune empty profiles
  await db.exec(`
    UPDATE device_profiles_v2
    SET deleted = 1
    WHERE id NOT IN (SELECT DISTINCT device_profile_id FROM device_profile_instances)
  `);

  if (emptyRows && emptyRows.length > 0) {
    for (let i = 0; i < emptyRows.length; i++) {
      const p = emptyRows[i];
      const pLabel = p.user_label || p.model || 'Unknown Profile';
      await addUserDeviceEdit({
        action_type: 'delete_profile',
        instance_ids: [],
        instance_summaries: [],
        source_profile_id: p.id,
        target_profile_id: null,
        source_profile_label: pLabel,
        target_profile_label: null,
        reason: 'Profile became empty and was deleted'
      });
    }
  }

  // Update attributes of remaining source profiles (if they were not pruned)
  for (let i = 0; i < sourceProfileIds.length; i++) {
    const srcId = sourceProfileIds[i];
    const checkSql = 'SELECT COUNT(*) as cnt FROM device_profiles_v2 WHERE id = ?';
    const checkRow = await db.exec(checkSql, { bind: [srcId], returnValue: 'resultRows', rowMode: 'object' });
    if (checkRow && checkRow[0] && checkRow[0].cnt > 0) {
      await updateProfileAttributes(db, srcId);
    }
  }

  // Log 1: Profile Creation
  await addUserDeviceEdit({
    action_type: 'create_profile',
    instance_ids: [],
    instance_summaries: [],
    source_profile_id: null,
    target_profile_id: newProfileId,
    source_profile_label: null,
    target_profile_label: newProfileLabel,
    reason: 'User created profile'
  });

  // Log 2: Move Instances
  await addUserDeviceEdit({
    action_type: 'move_instances',
    instance_ids: instanceIds,
    instance_summaries: instanceSummaries,
    source_profile_id: sourceProfileId,
    target_profile_id: newProfileId,
    source_profile_label: sourceProfileLabel,
    target_profile_label: newProfileLabel,
    reason: reason
  });

  return { status: 'ok', message: 'Created profile successfully', new_profile_id: newProfileId };
}
