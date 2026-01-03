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
}
