// custom to WISPR-lab/data-export-gui


import { getDB } from '../index.js';


export async function getEventMeta() {
  const db = await getDB();
  if (!db) {
    throw new Error('Database not initialized');
  }
  
  const countResult = await db.exec('SELECT COUNT(*) as count FROM events', 
    {returnValue: 'resultRows', rowMode: 'object'}
  );

  let mappings = [];
  let totalItems = 0
  if (countResult.length != 0) {
    mappings = await db.exec(
        'SELECT field, type FROM v_event_field_mappings ORDER BY field ASC', 
        { returnValue: 'resultRows', rowMode: 'object'}
    );
    totalItems = (countResult[0] && countResult[0].count) || 0;
  }
  
  return {
    mappings: mappings || [],
    attributes: {},
    filter_labels: [],
    count_per_index: {},
    emojis: {},
    search_node: null,
    total_items: totalItems
  };
}



export async function getDeviceMeta() {
    const db = await getDB();
    const mappings = await db.exec(
        'SELECT field, type FROM v_device_field_mappings ORDER BY field ASC', 
        { returnValue: 'resultRows', rowMode: 'object'}
    );
  
  const countResult = await db.exec('SELECT COUNT(*) as count FROM auth_devices_initial', 
    {returnValue: 'resultRows', rowMode: 'object'}
  );
  const totalItems = (countResult[0] && countResult[0].count) || 0;
  
  return {
    mappings: mappings || [],
    attributes: {},
    filter_labels: [],
    count_per_index: {},
    emojis: {},
    search_node: null,
    total_items: totalItems
  };
}