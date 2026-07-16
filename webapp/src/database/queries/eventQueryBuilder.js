// added for WISPR-lab/data-export-gui

import { parse as parseLiqe } from 'liqe';

export function buildWhereClause(filter = {}, queryString = '', stringColumns = []) {
  /* Composes search bar text, upload filters, datetime range, and attribute chips into a single WHERE clause. */
  const allConditions = [];
  const allParams = [];

  // 1. Text Search Bar Query
  if (queryString && queryString.trim()) {
    const { conditions, params } = compileSearchString(queryString, stringColumns);
    allConditions.push(...conditions);
    allParams.push(...params);
  }

  // 2. Upload Timeline Filters
  const { conditions: uploadConds, params: uploadParams } = compileUploadFilter(filter.uploadIds);
  allConditions.push(...uploadConds);
  allParams.push(...uploadParams);

  // 3. Time Filter Chips
  const { conditions: datetimeConds, params: datetimeParams } = compileTimeFilters(filter.chips);
  allConditions.push(...datetimeConds);
  allParams.push(...datetimeParams);

  // 4. Attribute / Tag / Label Chips
  const { conditions: filterConds, params: filterParams } = compileAttributeFilters(filter.chips, stringColumns);
  allConditions.push(...filterConds);
  allParams.push(...filterParams);

  const result = {
    clause: allConditions.length > 0 ? 'WHERE ' + allConditions.join(' AND ') : '',
    params: allParams
  };
  console.log('[buildWhereClause] Final WHERE:', result.clause);
  console.log('[buildWhereClause] Params:', result.params);
  return result;
}

export function buildOrderClause(options = {}) {
  const order = (options.order || 'desc').toUpperCase();
  const orderBy = options.orderBy || 'timestamp';
  
  const allowedColumns = ['timestamp', 'id', 'event_type_msg', 'category'];
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

// --- SEARCH STRING COMPILER (LUCENE) ---

function compileSearchString(searchString, stringColumns) {
  /* Parses the search bar string as Lucene syntax; falls back to global fuzzy search on parse failure. */
  if (!searchString || !searchString.trim()) {
    return { conditions: [], params: [] };
  }

  try {
    const ast = parseLiqe(searchString);
    return traverseSearchAST(ast, stringColumns);
  } catch (error) {
    console.warn('[compileSearchString] Parse error, falling back to global fuzzy search:', error);
    return compileGlobalFuzzySearch(searchString, stringColumns);
  }
}

function traverseSearchAST(node, stringColumns) {
  /* Recursively traverses the parsed Lucene AST tree and builds SQL conditions. */
  if (!node) return { conditions: [], params: [] };

  if (node.type === 'Tag') {
    const field = node.field && node.field.type === 'Field' ? node.field.name : null;
    const val = node.expression && node.expression.value !== undefined ? node.expression.value : '';
    const quoted = node.expression && node.expression.quoted === true;
    return compileFieldSearch(field, val, stringColumns, quoted);
  }

  if (node.type === 'LogicalExpression') {
    const left = traverseSearchAST(node.left, stringColumns);
    const right = traverseSearchAST(node.right, stringColumns);
    const op = node.operator && node.operator.operator ? node.operator.operator : 'AND';

    if (left.conditions.length > 0 && right.conditions.length > 0) {
      return {
        conditions: [`(${left.conditions[0]} ${op} ${right.conditions[0]})`],
        params: [...left.params, ...right.params]
      };
    } else if (left.conditions.length > 0) {
      return left;
    } else {
      return right;
    }
  }

  if (node.type === 'UnaryOperator') {
    const inner = traverseSearchAST(node.operand, stringColumns);
    if (inner.conditions.length > 0) {
      return {
        conditions: [`NOT (${inner.conditions[0]})`],
        params: inner.params
      };
    }
    return inner;
  }

  if (node.type === 'ParenthesizedExpression') {
    return traverseSearchAST(node.expression, stringColumns);
  }

  return { conditions: [], params: [] };
}

function compileFieldSearch(field, value, stringColumns, quoted = false) {
  /* Scopes search bar queries to columns or JSON attributes; supports exact matches for quoted terms. */
  if (field) {
    const matchedCol = stringColumns.find(col => col.split('.').pop() === field);
    if (quoted) {
      if (matchedCol) {
        return {
          conditions: [`LOWER(${matchedCol}) = ?`],
          params: [value.toLowerCase()]
        };
      } else {
        return {
          conditions: [`json_extract(e.attributes, '$.${field}') = ?`],
          params: [value]
        };
      }
    } else {
      const isWildcard = value.includes('*') || value.includes('?');
      const finalValue = wildcardToLike(value);
      const likeValue = isWildcard ? finalValue : `%${finalValue}%`;
      if (matchedCol) {
        return {
          conditions: [`LOWER(${matchedCol}) LIKE ? ESCAPE '|'`],
          params: [likeValue.toLowerCase()]
        };
      } else {
        return {
          conditions: [`json_extract(e.attributes, '$.${field}') LIKE ?`],
          params: [likeValue]
        };
      }
    }
  } else {
    return compileGlobalFuzzySearch(value, stringColumns);
  }
}

function compileGlobalFuzzySearch(text, stringColumns) {
  /* Helper to perform fuzzy LIKE search across all database columns and JSON attributes. */
  const isWildcard = text.includes('*') || text.includes('?');
  const finalValue = wildcardToLike(text);
  const likeValue = isWildcard ? finalValue : `%${finalValue}%`;
  
  const fieldConditions = stringColumns.map(f => `LOWER(${f}) LIKE ? ESCAPE '|'`);
  const lowerLikeValue = likeValue.toLowerCase();
  
  return {
    conditions: [`(${fieldConditions.join(' OR ')} OR json_extract(e.attributes, '$') LIKE ?)`],
    params: [...Array(stringColumns.length).fill(lowerLikeValue), likeValue]
  };
}

// --- STATE-BASED CHIP BUILDERS ---

function compileUploadFilter(uploadIds = []) {
  /* Restricts queries to specific upload timeline sources. */
  if (!Array.isArray(uploadIds)) {
    return { conditions: [], params: [] };
  }

  const ids = uploadIds.filter(id => (typeof id === 'string' || typeof id === 'number') && id !== '_all');
  if (ids.length === 0) {
    return { conditions: [], params: [] };
  }

  const placeholders = ids.map(() => '?').join(',');
  return {
    conditions: [`e.upload_id IN (${placeholders})`],
    params: ids
  };
}

function compileTimeFilters(chips = []) {
  /* Compiles date range chips into timestamp window restrictions. */
  if (!Array.isArray(chips) || chips.length === 0) {
    return { conditions: [], params: [] };
  }
  
  const activeDatetimeChips = chips.filter(
    chip => chip && chip.type && chip.type.startsWith('datetime') && chip.active !== false
  );
  if (activeDatetimeChips.length === 0) {
    return { conditions: [], params: [] };
  }

  const timeConditions = [];
  const params = [];

  activeDatetimeChips.forEach(chip => {
    const parts = chip.value.split(',');
    const startStr = parts[0];
    const endStr = parts[1];
    if (!startStr) return;

    const startMs = new Date(startStr).getTime();
    if (isNaN(startMs)) return;

    if (endStr) {
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

  if (timeConditions.length === 0) {
    return { conditions: [], params: [] };
  }

  return {
    conditions: ['(' + timeConditions.join(' OR ') + ')'],
    params
  };
}

function compileAttributeFilters(chips = [], stringColumns = []) {
  /* Compiles tags, labels, and attribute filter chips into exact database matches. */
  if (!Array.isArray(chips) || chips.length === 0) {
    return { conditions: [], params: [] };
  }

  const activeFilterChips = chips.filter(
    chip => chip && chip.type && (chip.type === 'tag' || chip.type === 'attribute' || chip.type === 'label') && chip.active !== false
  );

  if (activeFilterChips.length === 0) {
    return { conditions: [], params: [] };
  }

  const conditions = [];
  const params = [];

  activeFilterChips.forEach(chip => {
    const escapedValue = escapeLikePattern(chip.value);
    
    if (chip.type === 'tag') {
      conditions.push(`json_extract(e.tags, '$') LIKE ?`);
      params.push(`%"${escapedValue}"%`);
    } else if (chip.type === 'label') {
      if (chip.value === 'starred') {
        conditions.push(`e.starred = 1`);
      } else {
        conditions.push(`json_extract(e.labels, '$') LIKE ?`);
        params.push(`%"${escapedValue}"%`);
      }
    } else if (chip.type === 'attribute' && chip.field) {
      const matched = stringColumns.find(col => col.split('.').pop() === chip.field);
      const cond = matched ? `LOWER(${matched}) = ?` : `json_extract(e.attributes, '$.${chip.field}') = ?`;
      const param = matched ? chip.value.toLowerCase() : chip.value;

      if (chip.operator === 'must_not') {
        conditions.push(`NOT (${cond})`);
      } else {
        conditions.push(cond);
      }
      params.push(param);
    }
  });

  return { conditions, params };
}

// --- UTILITY STRING HELPERS ---

function escapeLikePattern(value) {
  if (typeof value !== 'string') return value;
  return value.replace(/\\/g, '\\\\').replace(/%/g, '\\%').replace(/_/g, '|_');
}

function wildcardToLike(term) {
  if (typeof term !== 'string') return term;
  const escaped = escapeLikePattern(term);
  return escaped.replace(/\*/g, '%').replace(/\?/g, '_');
}