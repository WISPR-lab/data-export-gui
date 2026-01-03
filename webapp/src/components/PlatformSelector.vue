<!--
Platform Selector Dialog for Data Upload

This component presents users with a choice of data export platforms,
explains the purpose of the tool, links to instructions, and then
proceeds to the file upload dialog.
-->
<template>
  <v-dialog
    v-model="dialog"
    persistent
    max-width="700px"
    @click:outside="closeDialog"
  >
    <template v-slot:activator="{ on, attrs }">
      <slot :attrs="attrs" :on="on"></slot>
    </template>

    <v-card>
      <!-- Step 1: Platform Selection -->
      <div v-if="step === 'platform-selection'" class="pa-8">
        <h2 class="text-h5 font-weight-medium mb-2">Select Your Platform</h2>
        <p class="text-body2 text-muted mb-6">
          Choose which service's data export you'd like to analyze. We support the following platforms:
        </p>

        <!-- Platform Grid -->
        <v-row class="mb-8">
          <v-col
            v-for="platform in platforms"
            :key="platform.id"
            cols="12"
            sm="6"
          >
            <v-card
              :outlined="selectedPlatformId !== platform.id"
              :color="selectedPlatformId === platform.id ? 'primary' : 'white'"
              class="platform-card pa-4 cursor-pointer"
              @click="selectPlatform(platform.id)"
              hover
            >
              <div class="d-flex align-center">
                <!-- Platform Logo/Icon -->
                <div class="platform-logo mr-4">
                  <v-icon size="48" :color="selectedPlatformId === platform.id ? 'white' : 'primary'">
                    {{ platform.icon }}
                  </v-icon>
                </div>

                <!-- Platform Info -->
                <div class="flex-grow-1">
                  <h3 class="text-body1 font-weight-medium" :class="selectedPlatformId === platform.id ? 'white--text' : ''">
                    {{ platform.name }}
                  </h3>
                  <p class="text-caption mb-0" :class="selectedPlatformId === platform.id ? 'white--text' : 'text-muted'">
                    {{ platform.description }}
                  </p>
                </div>

                <!-- Checkmark -->
                <v-icon
                  v-if="selectedPlatformId === platform.id"
                  color="white"
                  class="ml-2"
                >
                  mdi-check-circle
                </v-icon>
              </div>
            </v-card>
          </v-col>
        </v-row>

        <!-- How to Request Link -->
        <div class="mb-6 pa-4 bg-info-lighten rounded">
          <div class="d-flex align-center">
            <v-icon small class="mr-2">mdi-information-outline</v-icon>
            <p class="text-body2 mb-0">
              Don't have your data yet?
              <router-link to="/how-to-request" target="_blank" class="font-weight-medium">
                View step-by-step instructions
              </router-link>
              for requesting your data export.
            </p>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="d-flex justify-end gap-2">
          <v-btn
            text
            @click="closeDialog"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            @click="proceedToUpload"
            :disabled="!selectedPlatformId"
          >
            Next: Upload Data
            <v-icon right>mdi-arrow-right</v-icon>
          </v-btn>
        </div>
      </div>

      <!-- Step 2: File Upload (delegated to PlatformUploadForm with platform info) -->
      <div v-if="step === 'file-upload'" class="pa-0">
        <PlatformUploadForm
          :selectedPlatform="selectedPlatformId"
          @close="closeDialog"
          @success="handleUploadSuccess"
        />
      </div>
    </v-card>
  </v-dialog>
</template>

<script>
import PlatformUploadForm from './PlatformUploadForm.vue'

export default {
  name: 'PlatformSelector',
  components: {
    PlatformUploadForm,
  },
  data() {
    return {
      dialog: false,
      step: 'platform-selection', // 'platform-selection' or 'file-upload'
      selectedPlatformId: null,
      platforms: [
        {
          id: 'google',
          name: 'Google',
          icon: 'mdi-google',
          description: 'Gmail, Drive, Photos, Activity',
        },
        {
          id: 'discord',
          name: 'Discord',
          icon: 'mdi-discord',
          description: 'Messages, Servers, Activity',
        },
        {
          id: 'apple',
          name: 'Apple',
          icon: 'mdi-apple',
          description: 'iCloud, Messages, Activity',
        },
        {
          id: 'facebook',
          name: 'Facebook / Meta',
          icon: 'mdi-facebook',
          description: 'Posts, Messages, Activity',
        },
        {
          id: 'instagram',
          name: 'Instagram',
          icon: 'mdi-instagram',
          description: 'Posts, Messages, Activity',
        },
        {
          id: 'snapchat',
          name: 'Snapchat',
          icon: 'mdi-snapchat',
          description: 'Messages, Friends, Activity',
        },
      ],
    }
  },
  methods: {
    selectPlatform(platformId) {
      this.selectedPlatformId = platformId
    },
    proceedToUpload() {
      this.step = 'file-upload'
    },
    closeDialog() {
      this.dialog = false
      this.step = 'platform-selection'
      this.selectedPlatformId = null
    },
    handleUploadSuccess() {
      this.$emit('success')
      this.closeDialog()
    },
  },
}
</script>

<style scoped lang="scss">
.text-muted {
  color: rgba(0, 0, 0, 0.54);
}

.bg-info-lighten {
  background-color: #e3f2fd;
}

.platform-card {
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12);
  }
}

.platform-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 8px;
  background-color: rgba(25, 118, 210, 0.08);
}



// Dark mode support
:deep(.v-application--dark) {
  .text-muted {
    color: rgba(255, 255, 255, 0.54);
  }

  .bg-info-lighten {
    background-color: #1a237e;
  }

  .platform-logo {
    background-color: rgba(144, 202, 249, 0.12);
  }
}
</style>

