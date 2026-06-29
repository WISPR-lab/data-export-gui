import { parse as parseLiqe } from 'liqe';




export function buildWhereClause(filter = {}, queryString = '', stringColumns = []) {
  /* Composes string search, upload filter, datetime range, and chip conditions into a single WHERE clause with parameterized bindings. */
  const allConditions = [];
  const allParams = [];

  if (queryString && queryString.trim()) {
    const { conditions, params } = stringConditions(queryString, stringColumns);
    allConditions.push(...conditions);
    allParams.push(...params);
  }

  const { conditions: uploadConds, params: uploadParams } = uploadCondition(filter.uploadIds);
  allConditions.push(...uploadConds);
  allParams.push(...uploadParams);

  const { conditions: datetimeConds, params: datetimeParams } = datetimeChipCondition(filter.chips);
  allConditions.push(...datetimeConds);
  allParams.push(...datetimeParams);

  const { conditions: filterConds, params: filterParams } = otherChipConditions(filter.chips, stringColumns);
  allConditions.push(...filterConds);
  allParams.push(...filterParams);

  const result =  {
    clause: allConditions.length > 0 ? 'WHERE ' + allConditions.join(' AND ') : '',
    params: allParams
  };
  console.log('[buildWhereClause] Final WHERE:', result.clause);
  console.log('[buildWhereClause] Params:', result.params);
  return result;
}



//   Strings 

function escapeLikePattern(value) {
  if (typeof value !== 'string') return value;
  return value.replace(/\\/g, '\\\\').replace(/%/g, '\\%').replace(/_/g, '|_');
}

function wildcardToLike(term) {
  if (typeof term !== 'string') return term;
  const escaped = escapeLikePattern(term);
  return escaped.replace(/\*/g, '%').replace(/\?/g, '_');
}



function stringLeaf(field, value, stringColumns) {
  /* If field matches a known column, scopes LIKE to it; otherwise broadcasts LIKE across all stringColumns plus json_extract on attributes. */
  const isWildcard = value.includes('*') || value.includes('?');
  const likeValue = isWildcard ? value : `%${value}%`;
  
  if (field) {
    const matchedCol = stringColumns.find(col => {
      const colName = col.includes('.') ? col.split('.')[1] : col;
      return colName === field;
    });
    if (matchedCol) {
      const lowerLikeValue = likeValue.toLowerCase();
      return {
        conditions: [`LOWER(${matchedCol}) LIKE ? ESCAPE '|'`],
        params: [lowerLikeValue]
      };
    } else {
      return {
        conditions: [`json_extract(e.attributes, '$.${field}') LIKE ?`],
        params: [`%${value}%`]
      };
    }
  } else {
    const fieldConditions = stringColumns.map(f => `LOWER(${f}) LIKE ? ESCAPE '|'`);
    const lowerLikeValue = likeValue.toLowerCase();
    return {
      conditions: [`(${fieldConditions.join(' OR ')} OR json_extract(e.attributes, '$') LIKE ?)`],
      params: [...Array(stringColumns.length).fill(lowerLikeValue), `%${value}%`]
    };
  }
}


function astToConditions(ast, stringColumns) {
  /* Recursively walks a Liqe AST and converts each node to SQL conditions with parameterized bindings. */
  if (!ast) return { conditions: [], params: [] };

  if (ast.type === 'Tag') {
    const field = ast.field && ast.field.type === 'Field' ? ast.field.name : null;
    const val = ast.expression && ast.expression.value !== undefined ? ast.expression.value : '';
    const value = wildcardToLike(val);
    return stringLeaf(field, value, stringColumns);
  }

  if (ast.type === 'LogicalExpression') {
    const left = astToConditions(ast.left, stringColumns);
    const right = astToConditions(ast.right, stringColumns);
    const op = ast.operator && ast.operator.operator ? ast.operator.operator : 'AND';

    if (left.conditions.length > 0 && right.conditions.length > 0) {
      return {
        conditions: [`(${left.conditions.join(` ${op} `)} ${op} ${right.conditions.join(` ${op} `)})`],
        params: [...left.params, ...right.params]
      };
    } else if (left.conditions.length > 0) {
      return left;
    } else {
      return right;
    }
  }

  if (ast.type === 'UnaryOperator') {
    const inner = astToConditions(ast.operand, stringColumns);
    if (inner.conditions.length > 0) {
      return {
        conditions: [`NOT (${inner.conditions.join(' OR ')})`],
        params: inner.params
      };
    }
    return inner;
  }

  if (ast.type === 'ParenthesizedExpression') {
    return astToConditions(ast.expression, stringColumns);
  }

  return { conditions: [], params: [] };
}



export function stringConditions(queryString, stringColumns) {
  /* Parses queryString as Lucene syntax; falls back to literal LIKE search across all columns on parse failure. */
  if (!queryString || !queryString.trim()) {
    return { conditions: [], params: [] };
  }

  try {
    const ast = parseLiqe(queryString);
    return astToConditions(ast, stringColumns);
  } catch (error) {
    console.warn('[stringConditions] Parse error, falling back to literal search:', error);
    const escaped = escapeLikePattern(queryString);
    return stringLeaf(null, escaped, stringColumns);
  }
}


//   upload filter 



function uploadCondition(uploadIds = []) {
  if (!Array.isArray(uploadIds)) {
    return { conditions: [], params: [] };
  }

  const ids = uploadIds.filter(id => typeof id === 'string' && id !== '_all');
  
  if (ids.length === 0) {
    return { conditions: [], params: [] };
  }

  const placeholders = ids.map(() => '?').join(',');
  return {
    conditions: [`e.upload_id IN (${placeholders})`],
    params: ids
  };
}



// chips, datetime


function datetimeChipCondition(chips = []) {
  /* Extends date-only end values (YYYY-MM-DD) to 23:59:59.999 so the full day is included in the range. */
  if (!Array.isArray(chips) || chips.length === 0) {
    return { conditions: [], params: [] };
  }
  const activeDatetimeChips = chips.filter(chip => chip && chip.type && chip.type.startsWith('datetime') && chip.active !== false);
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




// other chip filters


function otherChipConditions(chips = [], stringColumns = []) {
  /* Routes tag/label chips to JSON LIKE queries and term chips to column-scoped stringLeaf conditions. */
  if (!Array.isArray(chips) || chips.length === 0) {
    return { conditions: [], params: [] };
  }

  const activeFilterChips = chips.filter(
    chip => chip && chip.type && (chip.type === 'tag' || chip.type === 'term' || chip.type === 'label') && chip.active !== false
  );

  if (activeFilterChips.length === 0) {
    return { conditions: [], params: [] };
  }

  const conditions = [];
  const params = [];

  activeFilterChips.forEach(chip => {
    const escapedValue = escapeLikePattern(chip.value);
    
    let cond = '';
    let termParams = [];
    if (chip.type === 'tag') {
      cond = `json_extract(e.tags, '$') LIKE ?`;
      termParams = [`%"${escapedValue}"%`];
    } else if (chip.type === 'label') {
      cond = `json_extract(e.labels, '$') LIKE ?`;
      termParams = [`%"${escapedValue}"%`];
    } else if (chip.type === 'term' && chip.field) {
      const { conditions: termConds, params: termParams } = stringLeaf(chip.field, escapedValue, stringColumns);
      if (termConds.length > 0) {
        if (chip.operator === 'must_not'){
        conditions.push(`NOT (${termConds.join(' OR ')})`);
      } else {
        conditions.push(...termConds); // ... AND ...
      }
      params.push(...termParams);
      }
    }
  });

  return { conditions, params };
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