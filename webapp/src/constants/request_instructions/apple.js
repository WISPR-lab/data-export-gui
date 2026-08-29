// added for anonymous-research-group/data-export-gui
import appleGetACopy from '@/assets/images/how2request/apple_get_a_copy.jpg'
import appleCategories from '@/assets/images/how2request/apple_categories.png'
import appleDownloadAll from '@/assets/images/how2request/apple_download_all.png'
import appleDownloadReady from '@/assets/images/how2request/apple_download_ready.png'
import appleNotAvailable from '@/assets/images/how2request/apple_not_available.jpg'

export const instructionApple = {
  id: 'apple',
  name: 'Apple',
  icon: 'mdi-apple',
  overview: 'Apple provides a data export through their Data and Privacy portal.',
  steps: [
    {
      title: 'Visit Apple Privacy and sign in',
      image: appleGetACopy,
      link: {
        url: 'https://privacy.apple.com',
        text: 'Apple Data & Privacy'
      },
      description: `Under the **\`Get a copy of your data\`** section, click **\`Request a copy of your data\`**.`
    },
    {
      title: 'Select security data categories',
      image: appleCategories,
      description: `1. Do not **\`Select all\`**. LEStrADE only parses security data, and smaller requests take less time.
2. Select the following 2 categories:
   - **\`Apple ID account and device information\`** (Login logs, password changes, passkeys, recovery contacts, device serial numbers & IMEIs)
   - **\`Marketing communications, downloads, and other data\`** (Includes data about old devices, but sometimes not available)
3. Click **\`Continue\`**.`
    },
    {
      title: 'Configure export settings',
      description: `1. Select **\`2GB\`** for maximum file size.
2. Click **\`Complete Request\`**.`
    },
    {
      title: 'Wait and download',
      images: [appleDownloadReady, appleDownloadAll],
      description: `1. Apple will email you when your data is ready (typically takes up to **7 days**).
   - Download links remain available for up to **75 days**.
2. Return to [Apple Privacy](https://privacy.apple.com) and click **\`Get your data\`**.
3. Click the download arrow next to each category.
   - You do not need to download the File Guides.
   - You can import individual ZIP files directly into LEStrADE.`
    },
    {
      title: 'If services are unavailable...',
      image: appleNotAvailable,
      description: `Apple services or categories (like "Other data") are sometimes temporarily unavailable. Apple will email you when they become available, but this often takes weeks, unfortunately.`
    }
  ]
}
