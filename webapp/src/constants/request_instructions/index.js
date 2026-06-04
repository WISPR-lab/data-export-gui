import { instructionGoogle } from './google'
import { instructionApple } from './apple'

export { instructionGoogle, instructionApple }

export const instructionRegistry = {
  google: instructionGoogle,
  apple: instructionApple,
  discord: {
    id: 'discord',
    name: 'Discord',
    comingSoon: true
  },
  facebook: {
    id: 'facebook',
    name: 'Facebook / Instagram',
    comingSoon: true
  },
  snapchat: {
    id: 'snapchat',
    name: 'Snapchat',
    comingSoon: true
  }
}
