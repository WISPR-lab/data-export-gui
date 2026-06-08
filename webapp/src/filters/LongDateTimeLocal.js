// added for WISPR-lab/data-export-gui
import dayjs from '@/plugins/dayjs'

export default {
  name: 'longDateTimeLocal',
  filter: function (ts) {
    if (!ts) return '';
    let dateInput = Number(ts);
    const strLen = parseInt(ts).toString().length;
    if (strLen === 10) {
      dateInput = dateInput * 1000;
    }
    
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZoneName: 'short'
    }).formatToParts(new Date(dateInput));
    const tzPart = parts.find(part => part.type === 'timeZoneName');
    const abbr = tzPart ? tzPart.value : 'UTC';
    
    return dayjs(dateInput).tz(tz).format('MMM D, YYYY   hh:mm A') + ` (${abbr})`;
  }
}
