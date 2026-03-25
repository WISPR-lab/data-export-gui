// custom to WISPR-lab/data-export-gui

import { parse as parseLucene } from 'lucene-query-parser';

function escapeLikePattern(value) {
  if (typeof value !== 'string') return value;
  return value.replace(/\\/g, '\\\\').replace(/%/g, '\\%').replace(/_/g, '|_');
}

function wildcardToLike(term) {
  if (typeof term !== 'string') return term;
  const escaped = escapeLikePattern(term);
  return escaped.replace(/\*/g, '%').replace(/\?/g, '_');
}

const flatColumns = ['id', 'timestamp', 'message', 'event_category', 'event_action', 'event_kind', 'platform'];

function astToConditions(ast) {
  if (!ast) return { conditions: [], params: [] };

  if (ast.left && !ast.operator_type) {
    return astToConditions(ast.left);
  }

  if (ast.term !== undefined) {
    const field = ast.field && ast.field !== '<implicit>' ? ast.field : null;
    const value = wildcardToLike(ast.term);
    const isWildcard = ast.term.includes('*') || ast.term.includes('?');
    const likeValue = isWildcard ? value : `%${value}%`;
    const lowerLikeValue = likeValue.toLowerCase();

    if (field && flatColumns.includes(field)) {
      return {
        conditions: [`LOWER(e.${field}) LIKE ? ESCAPE '|'`],
        params: [lowerLikeValue]
      };
    } else if (field) {
      return {
        conditions: [`json_extract(e.attributes, '$.${field}') LIKE ?`],
        params: [`%${value}%`]
      };
    } else {
      const searchFields = ['message', 'attributes', 'event_action', 'event_category', 'event_kind'];
      const fieldConditions = searchFields.map(f => `LOWER(e.${f}) LIKE ? ESCAPE '|'`);
      return {
        conditions: [`(${fieldConditions.join(' OR ')})`],
        params: Array(searchFields.length).fill(lowerLikeValue)
      };
    }
  }

  if (ast.operator_type === 'OR') {
    const left = astToConditions(ast.left);
    const right = astToConditions(ast.right);
    return {
      conditions: [`(${left.conditions.join(' OR ')} OR ${right.conditions.join(' OR ')})`],
      params: [...left.params, ...right.params]
    };
  }

  if (ast.operator_type === 'AND') {
    const left = astToConditions(ast.left);
    const right = astToConditions(ast.right);
    return {
      conditions: [`(${left.conditions.join(' AND ')} AND ${right.conditions.join(' AND ')})`],
      params: [...left.params, ...right.params]
    };
  }

  if (ast.operator_type === 'NOT') {
    const inner = astToConditions(ast.term);
    return {
      conditions: [`NOT (${inner.conditions.join(' AND ')})`],
      params: inner.params
    };
  }

  return { conditions: [], params: [] };
}

export function parseQueryString(queryString) {
  if (!queryString || !queryString.trim()) {
    return { conditions: [], params: [] };
  }

  try {
    const ast = parseLucene(queryString);
    return astToConditions(ast);
  } catch (error) {
    console.warn('[parseQueryString] Parse error, falling back to literal search:', error);
    const escaped = escapeLikePattern(queryString);
    const searchFields = ['message', 'attributes', 'event_action', 'event_category', 'event_kind'];
    const fieldConditions = searchFields.map(f => `LOWER(e.${f}) LIKE ? ESCAPE '|'`);
    return {
      conditions: [`(${fieldConditions.join(' OR ')})`],
      params: Array(searchFields.length).fill(`%${escaped}%`.toLowerCase())
    };
  }
}

export function buildWhereClause(filter = {}, queryString = '') {
  const conditions = [];
  const params = [];

  if (queryString && queryString.trim()) {
    const { conditions: queryConditions, params: queryParams } = parseQueryString(queryString);
    conditions.push(...queryConditions);
    params.push(...queryParams);
  }

  let uploadIds = filter.uploadIds || [];
  if (Array.isArray(uploadIds)) {
    uploadIds = uploadIds.filter(id => typeof id === 'string' && id !== '_all');
  }
  
  if (uploadIds.length > 0) {
    const placeholders = uploadIds.map(() => '?').join(',');
    conditions.push(`e.upload_id IN (${placeholders})`);
    params.push(...uploadIds);
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


    
    const filterChips = filter.chips.filter(
      chip => chip && chip.active !== false && (chip.type === 'tag' || chip.type === 'term' || chip.type === 'label')
    );
    
    filterChips.forEach(chip => {
      const escapedValue = escapeLikePattern(chip.value);
      const operator = chip.operator === 'must_not' ? 'NOT ' : '';
      
      if (chip.type === 'tag' || chip.type === 'label') {
        const field = chip.type === 'tag' ? 'tags' : 'labels';
        conditions.push(`${operator}json_extract(e.${field}, '$') LIKE ?`);
        params.push(`%"${escapedValue}"%`);
      } else if (chip.type === 'term' && chip.field) {
        if (flatColumns.includes(chip.field)) {
          conditions.push(`${operator}LOWER(e.${chip.field}) LIKE ? ESCAPE '|'`);
          params.push(`%${escapedValue}%`.toLowerCase());
        } else {
          conditions.push(`${operator}json_extract(e.attributes, '$.${chip.field}') LIKE ?`);
          params.push(`%"${escapedValue}"%`);
        }
      }
    });
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
  return result;
}
