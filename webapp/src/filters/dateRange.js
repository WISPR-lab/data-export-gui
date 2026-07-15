// added for WISPR-lab/data-export-gui
import dayjs from '@/plugins/dayjs'

// Formats a [firstVal, lastVal] pair as a compact date range string.
// Examples:
//   same day      → "Aug 24, 2025"
//   same year     → "Mar 6 – Aug 7, 2025"
//   different year → "Dec 1, 2024 – Jan 15, 2025"
export default {
  name: 'dateRange',
  filter: function (vals) {
    if (!Array.isArray(vals) || vals.length < 2) return '';
    var first = vals[0] ? dayjs.utc(vals[0]) : null;
    var last  = vals[1] ? dayjs.utc(vals[1]) : null;

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
