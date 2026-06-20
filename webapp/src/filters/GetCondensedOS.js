// added for WISPR-lab/data-export-gui
import { titleCase } from '@/filters/TitleCase.js';

export function getCondensedOS(osName, versions) {
  const name = osName || '';
  const list = (versions || []).filter(Boolean);
  if (!name) return [];
  const titleName = titleCase(name);
  if (list.length > 0) {
    const listCopy = [...list];
    listCopy.sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));
    return listCopy.map(function(v, idx) {
      return idx === 0 ? (titleName + ' ' + v) : v;
    });
  }
  return [titleName];
}

export default {
  name: 'getCondensedOS',
  filter: getCondensedOS
};
