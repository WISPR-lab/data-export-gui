// TODO: Apple images are missing from public/how2request/images/
// Referenced: apple_menu.jpg, apple_selection.jpg, apple_size.jpg, apple_email.jpg
// Add these images to src/assets/images/how2request/ and import them below

export const instructionApple = {
  id: 'apple',
  name: 'Apple',
  icon: 'mdi-apple',
  overview: 'Apple provides a data export through their Data and Privacy portal. Note that this process is stricter than Google\'s and may take longer to verify your identity.',
  steps: [
    {
      title: 'Visit Apple Privacy and sign in',
      link: {
        url: 'https://privacy.apple.com',
        text: 'Apple Data & Privacy'
      }
    },
    {
      title: 'Start the request',
      // image: appleMenu,  // TODO: Image file missing
      description: `1. Under the "Get a copy of your data" section, click **\`Request a copy of your data\`**.
2. This will open a list of available data categories.`
    },
    {
      title: 'Select security data categories',
      // image: appleSelection,  // TODO: Image file missing
      alert: {
        type: 'info',
        text: 'Apple **does not** export iMessage or text message content through this tool, as most are end-to-end encrypted. It only provides device registration metadata.'
      },
      description: `1. Scroll through the list. You do not need to "Select All." LEStrADE only parses security data, and smaller requests usually take less time.
2. Select the **2 security categories**:
   - **\`Apple ID account and device information\`** (Login logs, password changes, passkeys, recovery contacts, device serial numbers & IMEIs)
   - **\`App install and push notification activity\`** (Push notification IP network logs & locations)`
    },
    {
      title: 'Choose file size',
      // image: appleSize,  // TODO: Image file missing
      description: `- Click **\`Continue\`**.
- Apple will ask for a maximum file size to split the download.
- We recommend selecting **\`1GB\`** or **\`2GB\`** to ensure the files are manageable.
- Click **\`Complete Request\`**.`
    },
    {
      title: 'Wait and download',
      // image: appleEmail,  // TODO: Image file missing
      description: `- **Timeline**: Apple takes longer than Google. It typically takes **up to 7 days** to verify your identity and prepare the data.
- **Notification**: You will receive an email when the data is ready.
- **Retention**: The download link is valid for **14 days**.
- **Safety**: Download to a secure location and [permanently delete](https://support.apple.com/guide/icloud/delete-email-mm6b1a17e3/icloud) the notification email immediately after downloading if you share an account or device.`
    }
  ]
}
