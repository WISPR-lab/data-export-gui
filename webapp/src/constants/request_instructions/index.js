import { instructionGoogle } from './google'
import { instructionApple } from './apple'
import { instructionFacebook } from './facebook'
import { instructionDiscord } from './discord'
import { instructionSnapchat } from './snapchat'

export { instructionGoogle, instructionApple, instructionFacebook, instructionDiscord, instructionSnapchat }

export const instructionRegistry = {
  google: instructionGoogle,
  apple: instructionApple,
  discord: instructionDiscord,
  facebook: instructionFacebook,
  snapchat: instructionSnapchat
}
