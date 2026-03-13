// custom to WISPR-lab/data-export-gui

import { parse as parseLucene } from 'lucene-query-parser';

function escapeLikePattern(value) {
  if (typeof value !== 'string') return value;
  return value.replace(/\\/g, '\\\\').replace(/%/g, '\\%').replace(/_/g, '\\_');
}

function wildcardToLike(term) {
  if (typeof term !== 'string') return term;
  const escaped = escapeLikePattern(term);
  return escaped.replace(/\*/g, '%').replace(/\?/g, '_');
}

function astToConditions(ast, availableFields) {
  if (!ast) return { conditions: [], params: [] };

  // Unwrap single-node wrapper (when only left exists, no operator)
  if (ast.left && !ast.operator_type) {
    return astToConditions(ast.left, availableFields);
  }

  if (ast.term !== undefined) {
    const field = ast.field && ast.field !== '<implicit>' ? ast.field : null;
    const value = wildcardToLike(ast.term);
    const isWildcard = ast.term.includes('*') || ast.term.includes('?');
    const likeValue = isWildcard ? value : `%${value}%`;

    console.log('[astToConditions] Term:', ast.term, 'Field:', field, 'LikeValue:', likeValue);

    if (field && availableFields.includes(field)) {
      return {
        conditions: [`e.${field} LIKE ?`],
        params: [likeValue]
      };
    } else {
      const defaultFields = ['message', 'attributes', 'event_action', 'event_category', 'event_kind'];
      const fieldConditions = defaultFields.map(f => `e.${f} LIKE ?`);
      const result = {
        conditions: [`(${fieldConditions.join(' OR ')})`],
        params: Array(defaultFields.length).fill(likeValue)
      };
      console.log('[astToConditions] No field, using defaults. Conditions:', result.conditions, 'Params:', result.params);
      return result;
    }
  }

  if (ast.operator_type === 'OR') {
    const left = astToConditions(ast.left, availableFields);
    const right = astToConditions(ast.right, availableFields);
    return {
      conditions: [`(${left.conditions.join(' OR ')} OR ${right.conditions.join(' OR ')})`],
      params: [...left.params, ...right.params]
    };
  }

  if (ast.operator_type === 'AND') {
    const left = astToConditions(ast.left, availableFields);
    const right = astToConditions(ast.right, availableFields);
    return {
      conditions: [`(${left.conditions.join(' AND ')} AND ${right.conditions.join(' AND ')})`],
      params: [...left.params, ...right.params]
    };
  }

  if (ast.operator_type === 'NOT') {
    const inner = astToConditions(ast.term, availableFields);
    return {
      conditions: [`NOT (${inner.conditions.join(' AND ')})`],
      params: inner.params
    };
  }

  return { conditions: [], params: [] };
}

export function parseQueryString(queryString, availableFields = []) {
  if (!queryString || !queryString.trim()) {
    return { conditions: [], params: [] };
  }

  try {
    const ast = parseLucene(queryString);
    console.log('[parseQueryString] Input:', queryString, 'AST:', JSON.stringify(ast, null, 2));
    const result = astToConditions(ast, availableFields);
    console.log('[parseQueryString] Result conditions:', result.conditions, 'params:', result.params);
    return result;
  } catch (error) {
    console.warn('[parseQueryString] Parse error, falling back to literal search:', error);
    const escaped = escapeLikePattern(queryString);
    return {
      conditions: [`(e.message LIKE ? OR e.attributes LIKE ?)`],
      params: [`%${escaped}%`, `%${escaped}%`]
    };
  }
}

export function buildWhereClause(filter = {}, queryString = '', availableFields = []) {
  const conditions = [];
  const params = [];

  const fieldNames = Array.isArray(availableFields)
    ? availableFields.map(f => typeof f === 'string' ? f : f.field).filter(Boolean)
    : [];

  if (queryString && queryString.trim()) {
    const { conditions: queryConditions, params: queryParams } = parseQueryString(queryString, fieldNames);
    conditions.push(...queryConditions);
    params.push(...queryParams);
  }

  let uploadIds = filter.upload_id || filter.indices;
  if (uploadIds) {
    if (Array.isArray(uploadIds)) {
      uploadIds = uploadIds.filter(id => typeof id === 'string');
    } else if (typeof uploadIds === 'object' && uploadIds.__ob__) {
      uploadIds = null; 
    }
    
    if (uploadIds && Array.isArray(uploadIds) && uploadIds.length > 0) {
      const placeholders = uploadIds.map(() => '?').join(',');
      conditions.push(`e.upload_id IN (${placeholders})`);
      params.push(...uploadIds);
    }
  }


  if (filter.category) {
    const categories = Array.isArray(filter.category) ? filter.category : [filter.category];
    if (categories.length > 0) {
      const placeholders = categories.map(() => '?').join(',');
      conditions.push(`e.category IN (${placeholders})`);
      params.push(...categories);
    }
  }

  if (filter.labels && Array.isArray(filter.labels) && filter.labels.length > 0) {
    filter.labels.forEach(label => {
      conditions.push(`json_extract(e.labels, '$') LIKE ?`);
      params.push(`%"${escapeLikePattern(label)}"%`);
    });
  }

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


  if (filter.chips && Array.isArray(filter.chips)) {
    const activeTimeChips = filter.chips.filter(
      chip => chip && chip.active !== false && chip.type && chip.type.startsWith('datetime')
    );
    if (activeTimeChips.length > 0) {
      const timeConditions = [];
      activeTimeChips.forEach(chip => {
        const parts = chip.value.split(',');
        const startStr = parts[0];
        const endStr = parts[1];
        if (!startStr) return;

        const startMs = new Date(startStr).getTime();
        if (isNaN(startMs)) return;

        if (endStr) {
          // For date-only end strings (YYYY-MM-DD), extend to end of that UTC day
          const isDateOnly = endStr.length === 10 && !endStr.includes('T');
          const endMs = new Date(endStr).getTime() + (isDateOnly ? (24 * 60 * 60 * 1000 - 1) : 0);
          if (!isNaN(endMs)) {
            timeConditions.push('(e.timestamp >= ? AND e.timestamp <= ?)');
            params.push(startMs, endMs);
            return;
          }
        }
        timeConditions.push('e.timestamp >= ?');
        params.push(startMs);
      });

      if (timeConditions.length > 0) {
        conditions.push('(' + timeConditions.join(' OR ') + ')');
      }
    }
  }


  if (filter.event_kind) {
    conditions.push(`e.event_kind = ?`);
    params.push(filter.event_kind);
  }

  const result = {
    clause: conditions.length > 0 ? 'WHERE ' + conditions.join(' AND ') : '',
    params
  };
  console.log('[buildWhereClause] Final WHERE:', result.clause);
  console.log('[buildWhereClause] Params:', result.params);
  return result;
}


export function buildOrderClause(options = {}) {
  const order = (options.order || 'desc').toUpperCase();
  const orderBy = options.orderBy || 'timestamp';
  
  const allowedColumns = ['timestamp', 'id', 'message', 'category'];
  const column = allowedColumns.includes(orderBy) ? orderBy : 'timestamp';
  const direction = ['ASC', 'DESC'].includes(order) ? order : 'DESC';
  
  return `ORDER BY e.${column} ${direction}`;
}

export function buildPaginationClause(options = {}) {
  const limit = parseInt(options.size || 40, 10);
  const offset = parseInt(options.from || 0, 10);
  
  const result = {
    clause: 'LIMIT ? OFFSET ?',
    params: [limit, offset]
  };
  console.log('[buildPaginationClause]', result);
  return result;
}
