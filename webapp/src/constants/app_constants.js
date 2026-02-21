/*
 * Application Constants
 * Merges definitions.js and tag_metadata.js
 */

/* definitions.js content */
export const colorPickerPalette = [
  '#55efc4',
  '#81ecec',
  '#74b9ff',
  '#a29bfe',
  '#00b894',
  '#00cec9',
  '#0984e3',
  '#6c5ce7',
  '#ffeaa7',
  '#fab1a0',
  '#ff7675',
  '#fd79a8',
  '#fdcb6e',
  '#e17055',
  '#ff4d4d',
  '#fffa65',
  '#e84393',
  '#f6e58d',
  '#ffbe76',
  '#ff7979',
  '#badc58',
  '#dff9fb',
  '#f9ca24',
  '#f0932b',
  '#eb4d4b',
  '#6ab04c',
  '#c7ecee',
  '#7ed6df',
  '#e056fd',
  '#686de0',
  '#95afc0',
  '#22a6b3',
  '#4bcffa',
  '#34e7e4',
  '#0be881',
  '#ffdd59',
];

/* tag_metadata.js content */
export const tagMetadata = {
  malware: {
    weight: 100,
    type: 'danger',
    color: '#ff0000',
    description: 'Malware indicator',
  },
  bad: {
    weight: 90,
    type: 'danger',
    color: '#ff0000',
    description: 'Bad/malicious',
  },
  suspicious: {
    weight: 50,
    type: 'warning',
    color: '#ff9800',
    description: 'Suspicious activity',
  },
  good: {
    weight: 10,
    type: 'legit',
    color: '#4caf50',
    description: 'Legitimate/good',
  },
  legit: {
    weight: 10,
    type: 'legit',
    color: '#4caf50',
    description: 'Legitimate/good',
  },
  export: {
    weight: 100,
    type: 'info',
    color: '#2196f3',
    description: 'Exported/marked for export',
  },
  default: {
    weight: 0,
    type: 'default',
    color: '#808080',
    description: 'Generic tag',
  },
  regexes: {
    '^GROUPNAME': {
      weight: 100,
      type: 'danger',
      color: '#ff0000',
      description: 'Group-level indicator',
    },
    '^inv_': {
      weight: 80,
      type: 'warning',
      color: '#ff9800',
      description: 'Investigation tag',
    },
  },
};
