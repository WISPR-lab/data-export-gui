<template>
  <v-dialog v-model="dialog" max-width="600px" persistent>
    <v-card>
      <!-- Header -->
      <v-toolbar flat dense color="grey lighten-4" height="70">
        <v-icon left large class="text--primary">mdi-shield-account</v-icon>
        <v-toolbar-title class="text-h6 ma-4">Privacy & Visibility Settings</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon @click="handleClose">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <!-- Content -->
      <v-card-text class="pa-6">
        <!-- Main description -->
        <div class="mb-4">
          Your export may contain sensitive content like messages, contact names, search history. Choose how each category is displayed by default. You can change these at any time.
        </div>

        <div class="py-2"></div>

        <v-expansion-panels>
          <!-- Messages & Emails -->
          <v-expansion-panel>
            <v-expansion-panel-header>
              <div class="d-flex align-center">
                <v-icon left>mdi-email-multiple-outline</v-icon>
                <div class="px-4">Message Contents</div>
              </div>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
                <div class="text--secondary">
                    Controls visibility of the written contents of texts, direct messages, & emails. Images are not processed.
                </div>      
              <v-radio-group v-model="settings.messagesEmails" class="mt-2">
                <v-radio :label="LABELS.BLUR_BY_DEFAULT" :value="VALUES.BLUR_BY_DEFAULT"></v-radio>
                <v-radio :label="LABELS.SHOW_ALL" :value="VALUES.SHOW_ALL"></v-radio>
              </v-radio-group>
            </v-expansion-panel-content>
          </v-expansion-panel>

            <!-- Message Sender/Recipient Details -->
          <v-expansion-panel>
            <v-expansion-panel-header>
              <div class="d-flex align-center">
                <v-icon left>mdi-account-box-outline</v-icon>
                <div class="px-4">Contact Information</div>
              </div>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
                <div class="text--secondary">Controls visibility of sender and recipient details of messages (texts, direct messages, & emails) and friend/follower requests.</div>
              <v-radio-group v-model="settings.contactInfo" class="mt-2">
                <v-radio :label="LABELS.BLUR_BY_DEFAULT" :value="VALUES.BLUR_BY_DEFAULT"></v-radio>
                <v-radio :label="LABELS.SHOW_ALL" :value="VALUES.SHOW_ALL"></v-radio>
              </v-radio-group>
            </v-expansion-panel-content>
          </v-expansion-panel>

          <!-- Posts & Comments -->
          <v-expansion-panel>
            <v-expansion-panel-header>
                <div class="d-flex align-center">
                <v-icon left>mdi-thumb-up-outline</v-icon>
                <div class="px-4">Social Posts</div>
                </div>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
                <div class="text--secondary">Controls visibility of text contents of social posts, comments, and likes.</div>
                <v-radio-group v-model="settings.socialPosts" class="mt-2">
                    <v-radio :label="LABELS.BLUR_BY_DEFAULT" :value="VALUES.BLUR_BY_DEFAULT"></v-radio>
                    <v-radio :label="LABELS.SHOW_ALL" :value="VALUES.SHOW_ALL"></v-radio>
                </v-radio-group>
            </v-expansion-panel-content>
          </v-expansion-panel>

            <!-- Search History -->
          <v-expansion-panel>
            <v-expansion-panel-header>
              <div class="d-flex align-center">
                <v-icon left>mdi-history</v-icon>
                <div class="px-4">Search History</div>
              </div>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
                <div class="text--secondary">Controls visibility of text contents of searches.</div>
              <v-radio-group v-model="settings.searchHistory" class="mt-2">
                <v-radio :label="LABELS.BLUR_BY_DEFAULT" :value="VALUES.BLUR_BY_DEFAULT"></v-radio>
                <v-radio :label="LABELS.SHOW_ALL" :value="VALUES.SHOW_ALL"></v-radio>
              </v-radio-group>
            </v-expansion-panel-content>
          </v-expansion-panel>

        </v-expansion-panels>
      </v-card-text>

      <!-- Actions -->
      <v-card-actions class="pa-4">
        <v-spacer></v-spacer>
        <v-btn text @click="handleClose">
          Skip
        </v-btn>
        <v-btn color="primary" @click="handleSave">
          Save & Continue
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: 'PrivacySettingsModal',
  props: {
    value: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      LABELS: {
        SHOW_ALL: 'Show all unblurred',
        BLUR_BY_DEFAULT: 'Blur by default, click to unblur (Default)'
      },
      VALUES: {
        SHOW_ALL: 'showAll',
        BLUR_BY_DEFAULT: 'blurByDefault'
      },
      settings: {
        messagesEmails: 'blurByDefault',
        searchHistory: 'blurByDefault',
        socialPosts: 'blurByDefault',
        contactInfo: 'blurByDefault'
      }
    };
  },
  computed: {
    dialog: {
      get() {
        return this.value;
      },
      set(val) {
        this.$emit('input', val);
      }
    }
  },
  methods: {
    handleClose() {
      this.dialog = false;
      this.$emit('close');
    },
    handleSave() {
      // TODO: Save settings to store
      console.log('[PrivacySettings] Saved:', this.settings);
      this.handleClose();
    }
  }
};
</script>
