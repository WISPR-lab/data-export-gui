// added for WISPR-lab/data-export-gui

export function getCondensedModel(manufacturer, model) {
  const mfr = (manufacturer || '').trim();
  const mdl = (model || '').trim();
  if (mfr && mdl) {
    if (mdl.toLowerCase().startsWith(mfr.toLowerCase())) {
      return mdl;
    }
    return `${mfr} ${mdl}`;
  }
  return mdl || mfr || '';
}

export default {
  name: 'getCondensedModel',
  filter: getCondensedModel
};
