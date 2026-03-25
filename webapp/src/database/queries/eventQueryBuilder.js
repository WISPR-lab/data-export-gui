import { parse as parseLucene } from 'lucene-query-parser';




export function buildWhereClause(filter = {}, queryString = '', stringCols = []) {
  const allConditions = [];
  const allParams = [];

  if (queryString && queryString.trim()) {
    const { conditions, params } = stringConditions(queryString, stringCols);
    allConditions.push(...conditions);
    allParams.push(...params);
  }

  const { conditions: uploadConds, params: uploadParams } = uploadCondition(filter.uploadIds);
  allConditions.push(...uploadConds);
  allParams.push(...uploadParams);

  const { conditions: datetimeConds, params: datetimeParams } = datetimeChipCondition(filter.chips);
  allConditions.push(...datetimeConds);
  allParams.push(...datetimeParams);

  const { conditions: filterConds, params: filterParams } = otherChipConditions(filter.chips, stringCols);
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



function stringLeaf(field, value, stringCols) {
  const isWildcard = value.includes('*') || value.includes('?');
  const likeValue = isWildcard ? value : `%${value}%`;
  
  if (field) {
    const matchedCol = stringCols.find(col => col.split('.')[1] === field);
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
    const fieldConditions = stringCols.map(f => `LOWER(${f}) LIKE ? ESCAPE '|'`);
    const lowerLikeValue = likeValue.toLowerCase();
    return {
      conditions: [`(${fieldConditions.join(' OR ')} OR json_extract(e.attributes, '$') LIKE ?)`],
      params: [...Array(stringCols.length).fill(lowerLikeValue), `%${value}%`]
    };
  }
}


function astToConditions(ast, stringCols) {
  if (!ast) return { conditions: [], params: [] };

  if (ast.left && !ast.operator_type) {
    return astToConditions(ast.left, stringCols);
  }

  if (ast.term !== undefined) {
    const field = ast.field && ast.field !== '<implicit>' ? ast.field : null;
    const value = wildcardToLike(ast.term);
    return stringLeaf(field, value, stringCols);
  }

  if (ast.operator_type === 'OR') {
    const left = astToConditions(ast.left, stringCols);
    const right = astToConditions(ast.right, stringCols);
    return {
      conditions: [`(${left.conditions.join(' OR ')} OR ${right.conditions.join(' OR ')})`],
      params: [...left.params, ...right.params]
    };
  }

  if (ast.operator_type === 'AND') {
    const left = astToConditions(ast.left, stringCols);
    const right = astToConditions(ast.right, stringCols);
    return {
      conditions: [`(${left.conditions.join(' AND ')} AND ${right.conditions.join(' AND ')})`],
      params: [...left.params, ...right.params]
    };
  }

  if (ast.operator_type === 'NOT') {
    const inner = astToConditions(ast.term, stringCols);
    return {
      conditions: [`NOT (${inner.conditions.join(' AND ')})`],
      params: inner.params
    };
  }

  return { conditions: [], params: [] };
}



export function stringConditions(queryString, stringCols) {
  if (!queryString || !queryString.trim()) {
    return { conditions: [], params: [] };
  }

  try {
    const ast = parseLucene(queryString);
    return astToConditions(ast, stringCols);
  } catch (error) {
    console.warn('[stringConditions] Parse error, falling back to literal search:', error);
    const escaped = escapeLikePattern(queryString);
    return stringLeaf(null, escaped, stringCols);
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
  if (!Array.isArray(chips) || chips.length === 0) {
    return { conditions: [], params: [] };
  }

  const datetimeChips = chips.filter(chip => chip && chip.type && chip.type.startsWith('datetime'));
  if (datetimeChips.length === 0) {
    return { conditions: [], params: [] };
  }

  const timeConditions = [];
  const params = [];

  datetimeChips.forEach(chip => {
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


function otherChipConditions(chips = [], stringCols = []) {
  if (!Array.isArray(chips) || chips.length === 0) {
    return { conditions: [], params: [] };
  }

  const filterChips = chips.filter(
    chip => chip && chip.type && (chip.type === 'tag' || chip.type === 'term' || chip.type === 'label')
  );

  if (filterChips.length === 0) {
    return { conditions: [], params: [] };
  }

  const conditions = [];
  const params = [];

  filterChips.forEach(chip => {
    const escapedValue = escapeLikePattern(chip.value);
    
    if (chip.type === 'tag') {
      conditions.push(`json_extract(e.tags, '$') LIKE ?`);
      params.push(`%"${escapedValue}"%`);
    } else if (chip.type === 'label') {
      conditions.push(`json_extract(e.labels, '$') LIKE ?`);
      params.push(`%"${escapedValue}"%`);
    } else if (chip.type === 'term' && chip.field) {
      const { conditions: termConds, params: termParams } = stringLeaf(chip.field, escapedValue, stringCols);
      conditions.push(...termConds);
      params.push(...termParams);
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