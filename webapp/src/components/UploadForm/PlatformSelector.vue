<!--
Platform Selector Dialog

Presents users with a choice of data export platforms,
explains the purpose of the tool, links to instructions, and then
proceeds to the file upload dialog
-->
<template>
  <v-dialog
    v-model="dialog"
    persistent
    max-width="500px"
  >
    <template v-slot:activator="{ on, attrs }">
      <slot :attrs="attrs" :on="on"></slot>
    </template>

    <v-card>
      <!-- Step 1: Platform Selection -->
      <template v-if="step === 'platform-selection'">
        <v-card-title class="text-h6 font-weight-medium">
          Select a platform
          <v-spacer></v-spacer>
          <v-btn icon small @click="closeDialog">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text class="pt-0 pb-2">
          <p class="text-body2 text--secondary mb-5">
            Choose which service's data export you'd like to analyze. You can upload more data later.
          </p>

          <v-row dense class="mb-4">
            <v-col v-for="platform in platforms" :key="platform.id" cols="4">
              <v-card
                outlined
                hover
                :class="['platform-option pa-3', { 'platform-option--selected': selectedPlatformId === platform.id }]"
                @click="selectPlatform(platform.id)"
              >
                <div class="d-flex flex-column align-center">
                  <svg
                    v-if="platform.id === 'discord'"
                    class="platform-option__discord-icon mb-1"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path fill="currentColor" d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057.101 18.079.11 18.1.128 18.112a19.9 19.9 0 0 0 5.994 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/>
                  </svg>
                  <v-icon v-else size="28" class="mb-1" :color="selectedPlatformId === platform.id ? 'primary' : ''">
                    {{ platform.icon }}
                  </v-icon>
                  <span class="text-body2 font-weight-medium text-center">{{ platform.name }}</span>
                </div>
              </v-card>
            </v-col>
          </v-row>

          <v-alert dense text type="info" class="mb-0">
            Don't have your data yet?
            <router-link to="/how-to-request" target="_blank" class="font-weight-medium">
              View step-by-step instructions
            </router-link>
          </v-alert>
        </v-card-text>

        <v-card-actions class="pa-4 pt-2">
          <v-spacer></v-spacer>
          <v-btn text @click="closeDialog">Cancel</v-btn>
          <v-btn color="primary" :disabled="!selectedPlatformId" @click="proceedToUpload">
            Continue
            <v-icon right>mdi-arrow-right</v-icon>
          </v-btn>
        </v-card-actions>
      </template>

      <!-- Step 2: File Upload (delegated to PlatformUploadForm with platform info) -->
      <div v-if="step === 'file-upload'" class="pa-0">
        <PlatformUploadForm
          :selectedPlatform="selectedPlatformId"
          @close="closeDialog"
          @success="handleUploadSuccess"
        />
      </div>
    </v-card>

    <!-- Privacy Settings Modal (shown after upload completes) -->
    <!-- <PrivacySettingsModal
      v-model="showPrivacySettings"
      @close="finalizeUpload"
    /> -->
  </v-dialog>
</template>

<script>
import { PLATFORM_METADATA } from '../../utils/uploadFormUtils.js'
import PlatformUploadForm from './UploadForm.vue'
import PrivacySettingsModal from '../PrivacySettingsModal.vue'

export default {
  name: 'PlatformSelector',
  components: {
    PlatformUploadForm,
    PrivacySettingsModal,
  },
  data() {
    return {
      dialog: false,
      step: 'platform-selection',
      selectedPlatformId: null,
      showPrivacySettings: false,
    }
  },
  computed: {
    platforms() {
      return Object.entries(PLATFORM_METADATA).map(([id, meta]) => ({ id, ...meta }))
    },
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
      this.showPrivacySettings = true
    },
    finalizeUpload() {
      this.$emit('success')
      this.closeDialog()
    },
  },
}
</script>

<style scoped lang="scss">
.platform-option {
  cursor: pointer;
  transition: border-color 0.15s;

  &--selected {
    border-color: var(--v-primary-base) !important;
    background-color: rgba(25, 118, 210, 0.06) !important;

    .text-body2 {
      color: var(--v-primary-base);
    }
  }

  &__discord-icon {
    width: 28px;
    height: 28px;
    color: inherit;
  }
}
</style>

