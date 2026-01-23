<template>
  <div>
    <PageHeader />
    <v-divider></v-divider>

    <v-container max-width="900px" class="pa-8">
      <!-- Page Title -->
      <h1 class="text-h3 mb-8 font-weight-light">How to Request Your Data Exports</h1>

      <!-- Platform Selector -->
      <div class="d-flex flex-wrap gap-3 mb-12">
        <v-btn
          v-for="platform in platforms"
          :key="platform.id"
          :outlined="selectedPlatform.id !== platform.id"
          :color="selectedPlatform.id === platform.id ? 'primary' : ''"
          @click="selectedPlatform = platform"
          class="platform-btn"
          large
        >
          {{ platform.name }}
        </v-btn>
      </div>

      <v-divider class="mb-10"></v-divider>

      <!-- Steps -->
      <div class="steps-container">
        <div
          v-for="(step, index) in displayedSteps"
          :key="index"
          class="step-block mb-12"
        >
          <!-- Two-column layout: text left (50%), image right (50%) -->
          <div class="d-flex align-start">
            <!-- Left column: Step number and content -->
            <div class="step-content">
              <div class="d-flex align-start gap-4">
                <div class="step-number">{{ index + 1 }}</div>
                <div>
                  <h2 class="text-h5 font-weight-medium mb-2">{{ step.title }}</h2>

                  <!-- Link if provided -->
                  <div v-if="step.link" class="mb-3">
                    <a :href="step.link.url" target="_blank" rel="noopener noreferrer" class="primary--text">
                      {{ step.link.text }}
                      <v-icon x-small>mdi-open-in-new</v-icon>
                    </a>
                  </div>

                  <!-- Description (string or array) -->
                  <div v-if="step.description && typeof step.description === 'string'" class="text-body1">
                    {{ step.description }}
                  </div>

                  <div v-if="step.description && Array.isArray(step.description)" class="text-body1">
                    <div v-for="(item, i) in step.description" :key="i" class="mb-2 step-item">
                      {{ item }}
                    </div>
                  </div>

                  <!-- Alert if provided -->
                  <div v-if="step.alert" class="mt-4" style="max-width: 100%;">
                    <v-alert :type="step.alert.type || 'warning'" dense class="font-weight-medium">
                      {{ step.alert.text }}
                    </v-alert>
                  </div>
                </div>
              </div>
            </div>

            <!-- Right column: Image -->
            <div v-if="step.image" class="step-image-col">
              <img 
                :src="`/${step.image}`" 
                :alt="step.title" 
                class="step-image"
              />
            </div>
          </div>

          <!-- Divider between steps -->
          <v-divider class="my-8"></v-divider>
        </div>
      </div>

      <!-- Final Warning (after all steps) -->
      <!-- <div class="mx-16" style="max-width: 40%;">
        <v-alert type="info" dense class="font-weight-medium d-flex align-center">
          {{ FINAL_STEP_WARNING }}
        </v-alert> -->
      <!-- </div> -->
      <div class="mb-16"></div>
    </v-container>
  </div>
</template>

<script>
import PageHeader from '../components/Navigation/PageHeader.vue'

const FINAL_STEP_WARNING = 'This export contains your sensitive information about you. If someone gains access to this file, they could view your private messages, your location, and/or your search history. Treat it as securely as you would a password or financial records.'

export default {
  name: 'HowToRequest',
  components: {
    PageHeader,
  },
  data() {
    return {
      FINAL_STEP_WARNING,
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
              title: 'Visit Google Takeout and sign in',
              link: {
                url: 'https://takeout.google.com',
                text: 'Google Takeout'
              },
        
            },
            {
              title: 'Select data categories',
              description: [
                'Click "Deselect all" first',
                'Search for and select: Access log activity, My Activity, Google Account',
                'Optionally add Chrome, Mail, Messages, Pixel, and Profile if relevant. Note that Mail can significantly increase export size. If you do select Mail, limit to specific folders or recent dates'
              ],
              image: 'tutorial/google_json.jpg',
              alert: {
                type: 'info',
                text: 'If a category offers a "Multiple format" button and JSON is an option, you must select JSON for compatibility.'
              }
            },
            {
              title: 'Choose file type, frequency and destination',
              description: [
                'Destination: "Select download link via email"',
                'Frequency: "Export once"',
                'File type & size: .zip and 2GB recommended'
              ],
              image: 'tutorial/google_freq.jpg',
              alert: {
                type: 'warning',
                text: 'Anyone with access to this email could download your data.'
              }
            },
            {
              title: 'Create export',
              description: 'Review your selections and click "Create export".',
              //image: 'tutorial/google_create.jpg',
            },
            {
              title: 'Wait and download',
              description: [
                'Google will email when ready (usually 2 hours to several day).',
                'Download and save to a secure location.',
                'Your download link will be available for 7 days.'
              ],
              image: 'tutorial/google_takeout_email.jpg',
              alert: {
                type: 'warning',
                text: FINAL_STEP_WARNING
              }
            },
          ],
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
              description: [
                'This includes your messages and server membership records',
                'Discord may ask for password confirmation',
                'The export usually completes within 1-24 hours',
              ],
              link: {
                url: 'https://discord.com/app',
                text: 'Open Discord'
              },
              image: 'discord-step-3.png',
            },
            {
              title: 'Download Your Data',
              description: [
                'File is typically in .zip format',
                'Download to a secure device',
                'Delete any temporary copies from cloud storage',
              ],
              image: 'discord-step-4.png',
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
              description: [
                'Apple will send a verification code to your trusted device',
                'Complete two-factor authentication',
                'Select the categories you want to export',
              ],
              image: 'apple-step-3.png',
            },
            {
              title: 'Receive and Download',
              description: [
                'Check both email and device for notification',
                'Download link is valid for 7 days',
                'Save to a secure password-protected device',
              ],
              image: 'apple-step-4.png',
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
              description: [
                'Confirm your password for security',
                'Choose data format (HTML or JSON)',
                'Select date range for export (optional)',
                'Choose specific categories to include',
              ],
              image: 'facebook-step-3.png',
            },
            {
              title: 'Wait for Preparation and Download',
              description: [
                'Large exports may take up to 24 hours',
                'Download available for 7 days after preparation',
                'Transfer to secure storage immediately',
              ],
              image: 'facebook-step-4.png',
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
        //       description: [
        //         'Choose the data format (HTML or JSON)',
        //         'Select the date range if needed',
        //         'Choose categories to export',
        //       ]
        //     },
        //     {
        //       title: 'Complete and Download',
        //       description: 'Confirm your password, then wait for Instagram to prepare your data. You\'ll be notified when ready to download.',
        //       image: 'instagram-step-4.png',
        //       description: [
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
              description: [
                'Snapchat may ask for password confirmation',
                'Export includes messages, conversation history, and account details',
                'Processing typically takes 1-7 days',
              ],
              image: 'snapchat-step-3.png',
            },
            {
              title: 'Receive and Download Link',
              description: [
                'Check email for download notification',
                'Link remains active for a limited time',
                'Store on a secure, password-protected device',
              ],
              image: 'snapchat-step-4.png',
            },
          ],
          whatToExpect: [
            'Export time: 1-7 days',
            'File format: .zip archive with JSON files',
            'Includes: Messages, friends list, account description, usage stats',
            'Note: Some deleted messages may not be recoverable',
          ]
        },
      ],
    }
  },
  computed: {
    displayedSteps() {
      return this.selectedPlatform ? this.selectedPlatform.steps : []
    },
  },
  mounted() {
    // Set the first platform as default
    this.selectedPlatform = this.platforms[0]
  },
}
</script>

<style scoped lang="scss">

.step-number {
  font-size: 2.5rem;
  font-weight: 300;
  color: var(--v-primary-base);
  min-width: 60px;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
  min-width: 0;
  margin-right: 60px;
}

.step-image-col {
  flex: 1;
}

.step-image {
  width: 100%;
  max-width: 450px;
  max-height: 450px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  object-fit: contain;
}

.step-item {
  padding-left: 16px;
  border-left: 3px solid var(--v-primary-base);
  position: relative;

  &::before {
    content: '•';
    position: absolute;
    left: -8px;
    color: var(--v-primary-base);
  }
}

.step-block:last-child .v-divider {
  display: none;
}

</style>
