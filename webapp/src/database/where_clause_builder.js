// custom to WISPR-lab/data-export-gui

// Escapes special chars in LIKE patterns
function escapeLikePattern(value) {
  if (typeof value !== 'string') return value;
  return value.replace(/\\/g, '\\\\').replace(/%/g, '\\%').replace(/_/g, '\\_');
}

// Builds parameterized WHERE clause (prevents SQL injection)
export function buildWhereClause(filter = {}) {
  const conditions = [];
  const params = [];

  // Text search
  if (filter.query && filter.query.trim()) {
    const searchTerm = escapeLikePattern(filter.query.trim());
    conditions.push(`(e.message LIKE ? OR e.attributes LIKE ?)`);
    params.push(`%${searchTerm}%`, `%${searchTerm}%`);
  }

  // Upload ID filter
  if (filter.upload_id) {
    const uploadIds = Array.isArray(filter.upload_id) ? filter.upload_id : [filter.upload_id];
    if (uploadIds.length > 0) {
      const placeholders = uploadIds.map(() => '?').join(',');
      conditions.push(`e.upload_id IN (${placeholders})`);
      params.push(...uploadIds.map(id => parseInt(id, 10)));
    }
  }

  // Category filter
  if (filter.category) {
    const categories = Array.isArray(filter.category) ? filter.category : [filter.category];
    if (categories.length > 0) {
      const placeholders = categories.map(() => '?').join(',');
      conditions.push(`e.category IN (${placeholders})`);
      params.push(...categories);
    }
  }

  // Labels filter
  if (filter.labels && Array.isArray(filter.labels) && filter.labels.length > 0) {
    filter.labels.forEach(label => {
      conditions.push(`json_extract(e.labels, '$') LIKE ?`);
      params.push(`%"${escapeLikePattern(label)}"%`);
    });
  }

  // Date range filter
  if (filter.dateRange) {
    if (filter.dateRange.start) {
      conditions.push(`e.timestamp >= ?`);
      params.push(filter.dateRange.start);
    }
    if (filter.dateRange.end) {
      conditions.push(`e.timestamp <= ?`);
      params.push(filter.dateRange.end);
    }
  }

  // Event kind filter
  if (filter.event_kind) {
    conditions.push(`e.event_kind = ?`);
    params.push(filter.event_kind);
  }

  return {
    clause: conditions.length > 0 ? 'WHERE ' + conditions.join(' AND ') : '',
    params
  };
}

export function buildOrderClause(options = {}) {
  const order = (options.order || 'desc').toUpperCase();
  const orderBy = options.orderBy || 'timestamp';
  
  // Whitelist to prevent SQL injection
  const allowedColumns = ['timestamp', 'id', 'message', 'category'];
  const column = allowedColumns.includes(orderBy) ? orderBy : 'timestamp';
  const direction = ['ASC', 'DESC'].includes(order) ? order : 'DESC';
  
  return `ORDER BY e.${column} ${direction}`;
}

export function buildPaginationClause(options = {}) {
  const limit = parseInt(options.size || 40, 10);
  const offset = parseInt(options.from || 0, 10);
  
  return {
    clause: 'LIMIT ? OFFSET ?',
    params: [limit, offset]
  };
}
