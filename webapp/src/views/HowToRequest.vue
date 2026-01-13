<template>
  <v-app>
    <PageHeader />

    <v-divider></v-divider>

    <!-- Page Content -->
    <v-container max-width="900px" class="py-8">
      <!-- Page Header -->
      <div class="mb-8">
        <h1 class="text-h3 font-weight-light mb-2">How to Request Your Data</h1>
        <p class="text-h6 secondary--text">Step-by-step guides for downloading data exports from major platforms</p>
      </div>

      <!-- Platform Selection Buttons -->
      <div class="mb-8">
        <div class="d-flex flex-wrap gap-2">
          <v-btn
            v-for="platform in platforms"
            :key="platform.id"
            :outlined="selectedPlatform.id !== platform.id"
            :color="selectedPlatform.id === platform.id ? 'primary' : 'default'"
            @click="selectedPlatform = platform"
            class="platform-btn"
          >
            <v-icon left>{{ platform.icon }}</v-icon>
            {{ platform.name }}
          </v-btn>
        </div>
      </div>

      <!-- Platform Content -->
      <v-card class="elevation-1">
        <v-card-title class="text-h5">
          {{ selectedPlatform.name }} - Data Export Guide
        </v-card-title>
        
        <v-divider></v-divider>

        <v-card-text class="pa-8">
          <!-- Overview -->
          <div class="mb-8">
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
          </div>

          <!-- Step-by-step Instructions -->
          <div class="mb-8">
            <h2 class="text-h6 font-weight-medium mb-4">Steps to Request Your Data</h2>
            
            <v-timeline dense class="pt-0">
              <v-timeline-item
                v-for="(step, index) in selectedPlatform.steps"
                :key="index"
                :number="index + 1"
                small
              >
                <div>
                  <h3 class="font-weight-medium mb-2">{{ step.title }}</h3>
                  <p class="text-body2 mb-3">{{ step.description }}</p>
                  
                  <!-- Screenshot placeholder -->
                  <div v-if="step.screenshot" class="screenshot-placeholder mb-4">
                    <!-- TODO: Replace with actual screenshot images -->
                    <!-- Screenshot: {{ step.screenshot }} -->
                    <div class="d-flex align-center justify-center rounded pa-6" style="min-height: 200px;">
                      <div class="text-center">
                        <v-icon large class="mb-2">mdi-image-outline</v-icon>
                        <p class="text-caption secondary--text">Screenshot: {{ step.screenshot }}</p>
                      </div>
                    </div>
                  </div>

                  <!-- Additional details -->
                  <div v-if="step.details" class="ml-4 pl-2 border-left-2 border-primary">
                    <p v-for="(detail, i) in step.details" :key="i" class="text-body2 secondary--text mb-2">
                      • {{ detail }}
                    </p>
                  </div>
                </div>
              </v-timeline-item>
            </v-timeline>
          </div>

          <!-- What to Expect -->
          <div class="mb-8">
            <h2 class="text-h6 font-weight-medium mb-4">What to Expect</h2>
            <v-list dense>
              <v-list-item v-for="item in selectedPlatform.whatToExpect" :key="item">
                <v-list-item-content>
                  <v-list-item-title class="text-body2">{{ item }}</v-list-item-title>
                </v-list-item-content>
              </v-list-item>
            </v-list>
          </div>

          <!-- Important Considerations -->
          <div>
            <h2 class="text-h6 font-weight-medium mb-4">Important Considerations</h2>
            <v-alert
              outlined
              type="warning"
              class="mb-4"
            >
              <strong>Data Security:</strong> The data export will contain sensitive personal information. Follow safe storage practices provided in your appointment guidance.
            </v-alert>
            
            <div class="light-info-card pa-4 rounded">
              <h3 class="text-body2 font-weight-medium mb-2">Tips for Safe Handling:</h3>
              <ul class="text-body2 mb-0">
                <li>Request the export from a safe device and network</li>
                <li>Download to a password-protected USB drive or device</li>
                <li>Delete from device cloud syncing (e.g., Google Drive, iCloud)</li>
                <li>Keep the USB in a secure location between appointments</li>
                <li>Bring only to your appointment with your consultant</li>
              </ul>
            </div>
          </div>
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
          notes: 'The download can be large depending on your data volume. Consider selecting only the categories relevant to your investigation.',
          steps: [
            {
              title: 'Access Google Takeout',
              description: 'Visit Google Takeout at https://takeout.google.com and sign in with your account.',
              screenshot: 'google-step-1.png',
            },
            {
              title: 'Select Data Categories',
              description: 'Choose the specific categories you want to export. For security investigations, focus on "Mail", "Drive", "Activity records", and "Device information".',
              screenshot: 'google-step-2.png',
              details: [
                'Click "Deselect all" first to start fresh',
                'Select only categories relevant to your concerns',
                'Leave sensitive categories unchecked if not needed',
              ]
            },
            {
              title: 'Choose File Format and Delivery',
              description: 'Select the file format (typically .zip), file size limits, and delivery method.',
              screenshot: 'google-step-3.png',
              details: [
                'ZIP format is recommended for this analysis tool',
                'If data exceeds 50GB, select multiple files',
                'Choose download to your device (not email delivery)',
              ]
            },
            {
              title: 'Start Export',
              description: 'Click "Create export" to begin the process. Google will prepare your data, which may take several hours to days.',
              screenshot: 'google-step-4.png',
              details: [
                'You will receive a notification when ready',
                'Download from the email link or your Google Takeout history',
                'Save to your password-protected device',
              ]
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
              screenshot: 'discord-step-1.png',
            },
            {
              title: 'Navigate to Privacy & Safety',
              description: 'Scroll down in the left sidebar to find "Privacy & safety" section.',
              screenshot: 'discord-step-2.png',
            },
            {
              title: 'Request Data Export',
              description: 'Look for "Request all Explore My Data" button and click it. Discord will prepare an archive of your account information.',
              screenshot: 'discord-step-3.png',
              details: [
                'This includes your messages and server membership records',
                'Discord may ask for password confirmation',
                'The export usually completes within 1-24 hours',
              ]
            },
            {
              title: 'Download Your Data',
              description: 'Once ready, check your email or return to Discord to download the prepared archive.',
              screenshot: 'discord-step-4.png',
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
              screenshot: 'apple-step-1.png',
            },
            {
              title: 'Select "Data and Privacy"',
              description: 'Click on "Data and Privacy" to access your account information tools.',
              screenshot: 'apple-step-2.png',
            },
            {
              title: 'Choose "Download Your Data"',
              description: 'Select the option to download a copy of your data. Verify your identity when prompted.',
              screenshot: 'apple-step-3.png',
              details: [
                'Apple will send a verification code to your trusted device',
                'Complete two-factor authentication',
                'Select the categories you want to export',
              ]
            },
            {
              title: 'Receive and Download',
              description: 'Apple will prepare your data and send you a link via email to download. This process takes up to 7 days.',
              screenshot: 'apple-step-4.png',
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
          name: 'Facebook / Meta',
          icon: 'mdi-facebook',
          overview: 'Facebook (Meta) offers a comprehensive data download through your settings, including messages, photos, posts, and activity logs.',
          notes: 'The export may be very large. Consider selecting specific time periods or categories to limit file size.',
          steps: [
            {
              title: 'Open Facebook Settings',
              description: 'Click the menu icon (three horizontal lines) and go to Settings & privacy, then select Settings.',
              screenshot: 'facebook-step-1.png',
            },
            {
              title: 'Find "Your Information"',
              description: 'Look for "Your information" section, typically in the left sidebar under privacy controls.',
              screenshot: 'facebook-step-2.png',
            },
            {
              title: 'Download Your Information',
              description: 'Click "Download your information" to start the process. You\'ll be prompted to review your password.',
              screenshot: 'facebook-step-3.png',
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
              screenshot: 'facebook-step-4.png',
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
        {
          id: 'instagram',
          name: 'Instagram',
          icon: 'mdi-instagram',
          overview: 'Instagram allows data downloads through your account settings, providing access to your posts, messages, followers, and activity history.',
          notes: 'Instagram is now part of Meta, so the download process is similar to Facebook. Note that some data may be limited by privacy settings.',
          steps: [
            {
              title: 'Open Instagram Settings',
              description: 'Tap your profile icon, then tap the menu icon (three horizontal lines) and go to Settings and privacy.',
              screenshot: 'instagram-step-1.png',
            },
            {
              title: 'Navigate to Account Center',
              description: 'Look for "Account Center" in your settings, which manages your Meta account information.',
              screenshot: 'instagram-step-2.png',
            },
            {
              title: 'Select Download Your Information',
              description: 'Choose your Instagram account and select "Download your information" to begin the export.',
              screenshot: 'instagram-step-3.png',
              details: [
                'Choose the data format (HTML or JSON)',
                'Select the date range if needed',
                'Choose categories to export',
              ]
            },
            {
              title: 'Complete and Download',
              description: 'Confirm your password, then wait for Instagram to prepare your data. You\'ll be notified when ready to download.',
              screenshot: 'instagram-step-4.png',
              details: [
                'Processing typically takes hours to 24 hours',
                'Download link available for 7 days',
                'Transfer to a secure device immediately',
              ]
            },
          ],
          whatToExpect: [
            'Export time: Usually a few hours',
            'File format: .zip archive (HTML or JSON format)',
            'Includes: Posts, stories, direct messages, followers, activity',
            'Access duration: 7 days to download',
          ]
        },
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
              screenshot: 'snapchat-step-1.png',
            },
            {
              title: 'Navigate to Account Settings',
              description: 'Scroll to "Account" section and find options related to data and privacy.',
              screenshot: 'snapchat-step-2.png',
            },
            {
              title: 'Request Your Data',
              description: 'Look for "Download Explore My Data" option and request an export of your information.',
              screenshot: 'snapchat-step-3.png',
              details: [
                'Snapchat may ask for password confirmation',
                'Export includes messages, conversation history, and account details',
                'Processing typically takes 1-7 days',
              ]
            },
            {
              title: 'Receive and Download Link',
              description: 'Snapchat will send a download link to your registered email address.',
              screenshot: 'snapchat-step-4.png',
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


.screenshot-placeholder {
  border-radius: 4px;
  background-color: #f5f5f5;
}

.border-left-2 {
  border-left: 2px solid;
}

</style>
