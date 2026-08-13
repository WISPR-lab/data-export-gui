// added for WISPR-lab/data-export-gui
import dayjs from '@/plugins/dayjs';

function normalize(val) {
  if (val === null || val === undefined || val === '') return null;
  var num = Number(val);
  if (!isNaN(num)) {
    if (num < 10000000000) return num * 1000;
    return num;
  }
  return val;
}

export default {
  name: 'dateRange',
  filter: function (vals) {
    if (!Array.isArray(vals) || vals.length < 2) return '';
    var normFirst = normalize(vals[0]);
    var normLast  = normalize(vals[1]);
    var first = normFirst ? dayjs.utc(normFirst) : null;
    var last  = normLast  ? dayjs.utc(normLast)  : null;

    if (first && !first.isValid()) first = null;
    if (last  && !last.isValid())  last  = null;

    if (!first && !last) return '';
    if (!first) return last.format('MMM D, YYYY');
    if (!last)  return first.format('MMM D, YYYY');

    if (first.isSame(last, 'day')) return last.format('MMM D, YYYY');

    if (first.isSame(last, 'year')) {
      // "Mar 6 – Aug 7, 2025"
      return first.format('MMM D') + ' \u2013 ' + last.format('MMM D, YYYY');
    }

    // "Dec 1, 2024 – Jan 15, 2025"
    return first.format('MMM D, YYYY') + ' \u2013 ' + last.format('MMM D, YYYY');
  }
}
