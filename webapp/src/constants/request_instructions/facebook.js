// added for anonymous-research-group/data-export-gui
import metaExport from '@/assets/images/how2request/meta_export.png'
import metaCategories from '@/assets/images/how2request/meta_categories.png'

export const instructionFacebook = {
  id: 'facebook',
  name: 'Meta (Facebook & Instagram)',
  icon: 'mdi-facebook',
  overview: 'Meta allows you to download a copy of your account data through the Accounts Center for either Facebook or Instagram.',
  steps: [
    {
      title: 'Visit Accounts Center and sign in.',
      links: [{
        url: 'https://accountscenter.facebook.com',
        text: 'Facebook Accounts Center'
      },
      {
        url: 'https://accountscenter.instagram.com',
        text: 'Instagram Accounts Center'
      }],
      description: `Sign in with either your Facebook or Instagram credentials. One or both of these might be connected to your Meta account.`
    },
    {
      title: 'Export your information',
      image: metaExport,
      description: `1. Select **\`Your information and permissions\`** from the left navigation sidebar.
2. Click **\`Export your information\`**.
3. Click **\`Create export\`**.
4. If prompted to choose a profile, choose the Facebook or Instagram data you would like to export. (Do not chose "Meta." LEStrade does not currently support Meta account data, has a slightly different stucture.)
5. Choose **\`Export to device\`**.

In the next screen, make sure the email under \`Notify\` is correct and safe for you to access.`
    },
    {
      title: 'Select security data categories',
      description: `1. Select **\`Customize information\`**. LEStrADE only parses security data, and smaller requests usually take less time.
2. There are multiple sections of data that depend on the platform. In each section, select **\`Clear all\`** to deselect all data. Then select the following categories of security data:
  - Facebook
    - Under Personal information, select **\`Profile information\`**.
    - Under Security and login information, select **\`Security and login information\`** 
  - Instagram
    - Under Personal information, select: 
        - **\`Profile information\`**
        - **\`Device information\`**.
    - Under Security and login information, select **\`Login and profile creation\`**
3. Select **\`Save\`**.`
    },
    {
      title: 'Configure other export settings',
      image: metaCategories,
      description: `1. Set **\`Date Range\`** to **\`All time\`** or **\`Last year\`**, depending on your needs.
2. Set **\`Format\`** to **\`JSON\`** (required for automated parsing).
3.  **\`Media quality\`**  can stay unchanged since this export will contain no photos..
4. Click **\`Start Export\`**.`
    },
    {
      title: 'Wait and download',
      description: `- **Timeline**: Meta typically takes **a few hours up to 48 hours** to generate your download. You will receive an email and in-app notification when the file is ready.
- **Retention**: Download links expire after **4 days**.`
    }
  ]
}
