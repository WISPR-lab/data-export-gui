import googleJson from '@/assets/images/how2request/google_json.jpg'
import googleFreq from '@/assets/images/how2request/google_freq.jpg'
import googleCreate from '@/assets/images/how2request/google_create.jpg'
import googleEmail from '@/assets/images/how2request/google_takeout_email.jpg'

export const instructionGoogle = {
  id: 'google',
  name: 'Google',
  icon: 'mdi-google',
  overview: 'Google allows you to download a copy of your data through Google Takeout.',
  steps: [
    {
      title: 'Visit Google Takeout and sign in',
      link: {
        url: 'https://takeout.google.com',
        text: 'Google Takeout'
      }
    },
    {
      title: 'Select security data categories',
      image: googleJson,
      alert: {
        type: 'info',
        text: 'If a category offers a **Multiple format** button, click it and select **JSON** if available.'
      },
      description: `1. Click **\`Deselect all\`** first. LEStrADE only parses security data, and smaller requests usually take less time.
2. Select the main security data categories:
   - **\`Access Log Activity\`** (IP address & device connection logs)
   - **\`Google Account\`** (Login history, recovery email/phone updates, and security events)
3. **If using Android devices**:
   - **\`Android Device Configuration Service\`** (Hardware IDs, IMEI/serial numbers, and network connections)`
    },
    {
      title: 'Configure and Create Export',
      image: googleCreate,
      description: `1. Destination: Select **\`Send download link via email\`**.
2. Frequency: Select **\`Export once\`**.
3. File type & size: Select **\`.zip\`** and **\`2GB\`**.
4. Click **\`Create export\`**.`
    },
    {
      title: 'Wait and download',
      image: googleEmail,
      description: `- You don't need to stay on the page. Google will email you when the file is ready.
- The download link is usually valid for **7 days**.
- **Safety**: Download to a secure location and [permanently delete](https://support.google.com/mail/answer/7401?hl=en&sjid=14515300465516538433-NC) the notification email immediately after downloading if you share an account or device.`
    }
  ]
}
