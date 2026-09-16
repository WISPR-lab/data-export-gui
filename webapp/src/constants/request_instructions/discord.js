// added for WISPR-lab/data-export-gui
import discordSettings from '@/assets/images/how2request/discord_settings.jpg'
import discordRequest from '@/assets/images/how2request/discord_request.jpg'
// TODO: import discordCategories from '@/assets/images/how2request/discord_categories.jpg' once 3rd screenshot is added

export const instructionDiscord = {
  id: 'discord',
  name: 'Discord',
  icon: 'mdi-discord',
  overview: 'Discord provides a data export package through User Settings.',
  steps: [
    {
      title: 'Sign in to Discord and open settings',
      image: discordSettings,
      link: {
        url: 'https://discord.com/channels/@me',
        text: 'Discord'
      },
      description: `Click the gear icon (**\` Settings\`**) next to your username.`
    },
    {
      title: 'Select security data categories',
      image: discordRequest,
      description: `1. Select **\`Data & Privacy\`** from the left sidebar.
2. Scroll down to **\`Request my data\`**.
3. Select main categories of security data. LEStrADE only parses security data, and smaller requests usually take less time:
    - **\`Account\`**
    - **\`Your Activity\`**
4. Note that Discord only lets you request your data once every 30 days.`
    },
    {
      title: 'Select categories',
      // image: discordCategories, // TODO: 3rd screenshot
      description: `1. Select data categories:
   - TODO: List specific Discord categories once confirmed.`
    },
    {
      title: 'Wait and download',
      description: `- **Timeline**: Discord states it can take **up to 30 days**, though packages typically arrive within **2 to 7 days**.
- You will receive an email with a download link when ready.`
    }
  ]
}
