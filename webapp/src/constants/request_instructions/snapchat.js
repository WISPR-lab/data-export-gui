// added for anonymous-research-group/data-export-gui
export const instructionSnapchat = {
  id: 'snapchat',
  name: 'Snapchat',
  icon: 'mdi-snapchat',
  overview: 'Snapchat provides a data export package through the Snapchat Accounts portal.',
  steps: [
    {
      title: 'Visit Snapchat Account Settings and sign in',
      link: {
        url: 'https://accounts.snapchat.com',
        text: 'Snapchat Account Settings'
      },
      description: `If you're reditected to the home page, click the profile picture icon and visit **\`Account Settings\`**. From settings, select **\`My Data\`**.`
    },
    {
      title: 'Select security data categories',
      description: `1. Uncheck all categories first. LEStrADE only parses security data, and smaller requests usually take less time.
2. Turn on **\`Export JSON Files\`** and **\`User Information\`**.
3. Click **\`Next\`**.`
    },
    {
      title: 'Configure export settings',
      description: `1. Choose a date range that suits your needs.
2. Make sure the email address is correct and safe for you to access.
3. Click **\`Submit\`**.`
    },
    {
      title: 'Wait and download',
      description: `- Snapchat will email you when your data package is ready.
- Return to [accounts.snapchat.com](https://accounts.snapchat.com) to download your file.`
    }
  ]
}
