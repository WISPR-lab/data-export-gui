<template>
  <v-app>
    <PageHeader />

    <v-divider></v-divider>

    <!-- Page Content -->
    <v-container max-width="900px" class="py-8">
      <!-- Page Header -->
      <h2 class="text-h3 mb-8">How to Request Your Data Exports</h2>
      <!-- Platform Selection Buttons -->
      <div class="d-flex flex-wrap gap-2 mb-8">
          <v-btn
            v-for="platform in platforms"
            :key="platform.id"
            :outlined="selectedPlatform.id !== platform.id"
            :color="selectedPlatform.id === platform.id ? 'primary' : 'default'"
            @click="selectedPlatform = platform"
            class="platform-btn"
            large
          >
            <!-- <v-icon left>{{ platform.icon }}</v-icon> -->
            {{ platform.name }}
          </v-btn>
      </div>
      
      <!-- Platform Content -->
      <v-card class="elevation-1">
        <v-card-title class="text-h5 font-weight-medium mb-4">
          {{ selectedPlatform.name }} - Steps to request your data
        </v-card-title>
        
        <!-- <v-divider></v-divider>

        <v-card-text class="pa-4"> -->
          <!-- Overview -->
          <!-- <div class="mb-8">
            <h2 class="text-h6 font-weight-medium mb-4">Overview</h2>
            <p class="text-body1 line-height-relaxed">{{ selectedPlatform.overview }}</p>
            <v-alert
              v-if="selectedPlatform.notes"
              outlined
              type="info"
              class="mt-4"
            >
              <strong>Note:</strong> {{ selectedPlatform.notes }}
            </v-alert>
          </div> -->

          <!-- Step-by-step Instructions -->
          <div class="mb-8">
            <!-- <h2 class="text-h6 font-weight-medium mb-4">{{ selectedPlatform.name }} - Steps to Request Your Data</h2> -->
            
            <v-timeline dense class="pt-0">
              <v-timeline-item
                v-for="(step, index) in selectedPlatform.steps"
                :key="index"
                :number="index + 1"
                small
              >
                <div>
                  <h3 class="font-weight-medium mb-2">{{ step.title }}</h3>
                  
                  <!-- Link if provided -->
                  <div v-if="step.link" class="mb-3">
                    <a :href="step.link.url" target="_blank" rel="noopener noreferrer" class="primary--text">
                      {{ step.link.text || 'Visit website' }}
                      <v-icon x-small>mdi-open-in-new</v-icon>
                    </a>
                  </div>
                  
                  <p v-if="step.description && typeof step.description === 'string'" class="text-body2 mb-3">{{ step.description }}</p>
                  
                  <!-- Description as array (paragraph with line breaks) -->
                  <p v-if="step.description && Array.isArray(step.description)" class="text-body2 mb-3">
                    <span v-for="(item, i) in step.description" :key="i">
                      {{ item }}<br v-if="i < step.description.length - 1" />
                    </span>
                  </p>
                  
                  <!-- Alert if provided -->
                  <v-alert v-if="step.alert" :type="step.alert.type || 'warning'" dense class="mt-3 mb-3 font-weight-medium">
                    {{ step.alert.text }}
                  </v-alert>
                  
                  <!-- Image -->
                  <div v-if="step.image" class="mb-4 elevation-2" style="display: inline-block; border-radius: 4px; overflow: hidden;">
                    <img 
                      :src="`/${step.image}`" 
                      :alt="step.title" 
                      style="max-width: 100%; max-height: 400px; display: block;"
                      @error="(e) => e.target.style.display = 'none'"
                    />
                  </div>
                </div>
              </v-timeline-item>
            </v-timeline>
          </div>

          <!-- Tips for Safe Handling -->
          <v-card outlined class="mb-8">
            <v-card-title class="text-body2 font-weight-medium">Tips for Safe Handling</v-card-title>
            <v-divider></v-divider>
            <v-list dense>
              <v-list-item>
                <v-list-item-content>
                  <v-list-item-title class="text-body2">Ensure the device you're downloading on is password-protected and secure</v-list-item-title>
                </v-list-item-content>
              </v-list-item>
              <v-list-item>
                <v-list-item-content>
                  <v-list-item-title class="text-body2">Be aware that cloud services (OneDrive, Google Drive, Box, iCloud) may automatically sync this file to your account, making it accessible from other devices or by anyone with access to that account.</v-list-item-title>
                </v-list-item-content>
              </v-list-item>
              <v-list-item>
                <v-list-item-content>
                  <v-list-item-title class="text-body2">Delete the file from your device after you're done using it</v-list-item-title>
                </v-list-item-content>
              </v-list-item>
            </v-list>
          </v-card>

        </v-card-text>
      </v-card>

      <!-- Help Section -->
      <div class="mt-8 text-center">
        <p class="text-body2 secondary--text mb-2">Need help? Contact your consultant for additional guidance.</p>
      </div>
    </v-container>
  </v-app>
</template>

<script>
import PageHeader from '../components/Navigation/PageHeader.vue'

export default {
  name: 'HowToRequest',
  components: {
    PageHeader,
  },
  data() {
    return {
      selectedPlatform: null,
      platforms: [
        {
          id: 'google',
          name: 'Google',
          icon: 'mdi-google',
          overview: 'Google allows you to download a copy of your data through Google Takeout, which includes your Gmail, Google Photos, Google Drive, and other Google services.',
          notes: 'The download can be large depending on your data volume.',
          steps: [
            {
              title: '1. Visit Google Takeout and sign in',
              link: {
                url: 'https://takeout.google.com',
                text: 'Google Takeout'
              },
        
            },
            {
              title: '2. Select data categories',
              description: [
                'Click "Deselect all" first',
                'Search for and select: Access log activity, My Activity, Google Account',
                'Optionally add Chrome, Mail, Messages, Pixel, and Profile if relevant. Note that Mail can significantly increase export size. If selected, limit to specific folders or recent dates'
              ],
              image: 'tutorial/google_json.jpg',
              alert: {
                type: 'info',
                text: 'If a category offers a "Multiple format" button and JSON is an option, you must select JSON for compatibility.'
              }
            },
            {
              title: '3. Choose file type, frequency and destination',
              description: [
                'Destination: "Select download link via email"',
                'Frequency: "Export once"',
                'File type & size: .zip and 2GB recommended'
              ],
              image: 'google-step-3.png',
              alert: {
                type: 'error',
                text: 'Anyone with access to this email could download your data.'
              }
            },
            {
              title: '4. Create export',
              description: 'Click "Create export" to start.',
              image: 'google-step-4.png',
            },
            {
              title: '5. Wait and download',
              description: 'Google will email when ready (usually hours to 1 day). Download and save to a secure location. Export time typically takes 2 hours to several days depending on your data volume. Your download link will be available for 7 days.',
              image: 'google-step-5.png',
              alert: {
                type: 'warning',
                text: 'This export contains your complete digital activity and personal information across platforms. If someone gains access, they could read your private messages, see your location history, and view your search activity. Treat it as securely as you would a password or financial records.'
              }
            },
          ],
          whatToExpect: [
            'Export time: 2 hours to several days depending on data volume',
            'File format: .zip archive containing all selected data',
            'File size: Can range from MB to several GB',
            'Access duration: Download link typically available for 7 days',
          ]
        },
        {
          id: 'discord',
          name: 'Discord',
          icon: 'mdi-discord',
          overview: 'Discord provides a data export feature in your account settings that includes your messages, servers, direct messages, and activity history.',
          notes: 'Discord exports are processed relatively quickly, usually within minutes to hours.',
          steps: [
            {
              title: 'Open Discord Settings',
              description: 'Click the settings gear icon next to your username in the bottom left corner.',
              image: 'discord-step-1.png',
            },
            {
              title: 'Navigate to Privacy & Safety',
              description: 'Scroll down in the left sidebar to find "Privacy & safety" section.',
              image: 'discord-step-2.png',
            },
            {
              title: 'Request Data Export',
              description: 'Look for "Request all Explore My Data" button in Privacy & Safety. Discord will prepare an archive of your account information.',
              link: {
                url: 'https://discord.com/app',
                text: 'Open Discord'
              },
              image: 'discord-step-3.png',
              details: [
                'This includes your messages and server membership records',
                'Discord may ask for password confirmation',
                'The export usually completes within 1-24 hours',
              ]
            },
            {
              title: 'Download Your Data',
              description: 'Once ready, check your email or return to Discord to download the prepared archive.',
              image: 'discord-step-4.png',
              details: [
                'File is typically in .zip format',
                'Download to a secure device',
                'Delete any temporary copies from cloud storage',
              ]
            },
          ],
          whatToExpect: [
            'Export time: Usually 1-24 hours',
            'File format: .zip archive with JSON files',
            'Includes: Messages, servers, users interactions',
            'Access duration: Limited time to download after preparation',
          ]
        },
        {
          id: 'apple',
          name: 'Apple',
          icon: 'mdi-apple',
          overview: 'Apple provides a comprehensive data export through their Data and Privacy portal, including iCloud data, App activity, and device information.',
          notes: 'Apple processes data exports within a specified timeframe (typically 7 days). You\'ll need to verify your identity.',
          steps: [
            {
              title: 'Visit Privacy.apple.com',
              description: 'Go to https://privacy.apple.com and sign in with your Apple ID.',
              image: 'apple-step-1.png',
            },
            {
              title: 'Select "Data and Privacy"',
              description: 'Click on "Data and Privacy" to access your account information tools.',
              image: 'apple-step-2.png',
            },
            {
              title: 'Choose "Download Your Data"',
              description: 'Select the option to download a copy of your data. Verify your identity when prompted.',
              image: 'apple-step-3.png',
              details: [
                'Apple will send a verification code to your trusted device',
                'Complete two-factor authentication',
                'Select the categories you want to export',
              ]
            },
            {
              title: 'Receive and Download',
              description: 'Apple will prepare your data and send you a link via email to download. This process takes up to 7 days.',
              image: 'apple-step-4.png',
              details: [
                'Check both email and device for notification',
                'Download link is valid for 7 days',
                'Save to a secure password-protected device',
              ]
            },
          ],
          whatToExpect: [
            'Processing time: Up to 7 days',
            'File format: .zip archive',
            'Includes: iCloud photos, mail, contacts, calendar data, device logs',
            'Identity verification: Required (2FA)',
          ]
        },
        {
          id: 'facebook',
          name: 'Facebook / Instagram',
          icon: 'mdi-facebook',
          overview: 'Facebook (Meta) offers a comprehensive data download through your settings, including messages, photos, posts, and activity logs.',
          notes: 'The export may be very large.',
          steps: [
            {
              title: 'Open Facebook Settings',
              description: 'Click the menu icon (three horizontal lines) and go to Settings & privacy, then select Settings.',
              image: 'facebook-step-1.png',
            },
            {
              title: 'Find "Your Information"',
              description: 'Look for "Your information" section, typically in the left sidebar under privacy controls.',
              image: 'facebook-step-2.png',
            },
            {
              title: 'Download Your Information',
              description: 'Click "Download your information" to start the process. You\'ll be prompted to review your password.',
              image: 'facebook-step-3.png',
              details: [
                'Confirm your password for security',
                'Choose data format (HTML or JSON)',
                'Select date range for export (optional)',
                'Choose specific categories to include',
              ]
            },
            {
              title: 'Wait for Preparation and Download',
              description: 'Facebook will prepare your data archive. You\'ll be notified when ready, usually within hours.',
              image: 'facebook-step-4.png',
              details: [
                'Large exports may take up to 24 hours',
                'Download available for 7 days after preparation',
                'Transfer to secure storage immediately',
              ]
            },
          ],
          whatToExpect: [
            'Export time: Usually a few hours, up to 24 hours for large exports',
            'File format: .zip archive (HTML or JSON format)',
            'File size: Can be very large depending on account activity',
            'Includes: Messages, photos, posts, activity, connections',
          ]
        },
        // {
        //   id: 'instagram',
        //   name: 'Instagram',
        //   icon: 'mdi-instagram',
        //   overview: 'Instagram allows data downloads through your account settings, providing access to your posts, messages, followers, and activity history.',
        //   notes: 'Instagram is now part of Meta, so the download process is similar to Facebook. Note that some data may be limited by privacy settings.',
        //   steps: [
        //     {
        //       title: 'Open Instagram Settings',
        //       description: 'Tap your profile icon, then tap the menu icon (three horizontal lines) and go to Settings and privacy.',
        //       image: 'instagram-step-1.png',
        //     },
        //     {
        //       title: 'Navigate to Account Center',
        //       description: 'Look for "Account Center" in your settings, which manages your Meta account information.',
        //       image: 'instagram-step-2.png',
        //     },
        //     {
        //       title: 'Select Download Your Information',
        //       description: 'Choose your Instagram account and select "Download your information" to begin the export.',
        //       image: 'instagram-step-3.png',
        //       details: [
        //         'Choose the data format (HTML or JSON)',
        //         'Select the date range if needed',
        //         'Choose categories to export',
        //       ]
        //     },
        //     {
        //       title: 'Complete and Download',
        //       description: 'Confirm your password, then wait for Instagram to prepare your data. You\'ll be notified when ready to download.',
        //       image: 'instagram-step-4.png',
        //       details: [
        //         'Processing typically takes hours to 24 hours',
        //         'Download link available for 7 days',
        //         'Transfer to a secure device immediately',
        //       ]
        //     },
        //   ],
        //   whatToExpect: [
        //     'Export time: Usually a few hours',
        //     'File format: .zip archive (HTML or JSON format)',
        //     'Includes: Posts, stories, direct messages, followers, activity',
        //     'Access duration: 7 days to download',
        //   ]
        // },
        {
          id: 'snapchat',
          name: 'Snapchat',
          icon: 'mdi-snapchat',
          overview: 'Snapchat provides data exports through their account settings, including message history, friend lists, account information, and usage data.',
          notes: 'Snapchat processes exports relatively quickly, but note that some message content may be limited by their retention policies.',
          steps: [
            {
              title: 'Open Snapchat Settings',
              description: 'Go to your profile page and tap the gear icon to access Settings.',
              image: 'snapchat-step-1.png',
            },
            {
              title: 'Navigate to Account Settings',
              description: 'Scroll to "Account" section and find options related to data and privacy.',
              image: 'snapchat-step-2.png',
            },
            {
              title: 'Request Your Data',
              description: 'Look for "Download Explore My Data" option and request an export of your information.',
              image: 'snapchat-step-3.png',
              details: [
                'Snapchat may ask for password confirmation',
                'Export includes messages, conversation history, and account details',
                'Processing typically takes 1-7 days',
              ]
            },
            {
              title: 'Receive and Download Link',
              description: 'Snapchat will send a download link to your registered email address.',
              image: 'snapchat-step-4.png',
              details: [
                'Check email for download notification',
                'Link remains active for a limited time',
                'Store on a secure, password-protected device',
              ]
            },
          ],
          whatToExpect: [
            'Export time: 1-7 days',
            'File format: .zip archive with JSON files',
            'Includes: Messages, friends list, account details, usage stats',
            'Note: Some deleted messages may not be recoverable',
          ]
        },
      ],
    }
  },
  mounted() {
    // Set the first platform as default
    this.selectedPlatform = this.platforms[0]
  },
}
</script>

<style scoped lang="scss">

.platform-btn {
  text-transform: none;
}

</style>
