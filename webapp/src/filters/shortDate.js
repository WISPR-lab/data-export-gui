// added for WISPR-lab/data-export-gui
import dayjs from '@/plugins/dayjs'

export default {
  name: 'shortDate',
  filter: function (val) {
    if (!val) return '';
    var d = dayjs.utc(val);
    return d.isValid() ? d.format('MMM D, YYYY') : '';
  }
}
