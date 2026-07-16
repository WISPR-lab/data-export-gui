<!--
Platform Selector Dialog

Presents users with a choice of data export platforms,
explains the purpose of the tool, links to instructions, and then
proceeds to the file upload dialog

Added for WISPR Lab / data-export-gui project
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

    <v-card rounded="lg" class="platform-selector-card">
      <!-- Step 1: Platform Selection -->
      <template v-if="step === 'platform-selection'">
        <v-card-title class="text-h6 font-weight-medium pb-2">
          Select a platform
          <v-spacer></v-spacer>
          <v-btn icon small @click="closeDialog"><v-icon>mdi-close</v-icon></v-btn>
        </v-card-title>

        <v-card-text class="pt-0 pb-2">
          <p class="text-body-2 text--secondary mb-4">
            Choose which service's data export you'd like to analyze. You can upload more data later.
          </p>

          <v-alert dense text type="success" icon="mdi-lock" class="mb-6 text-body-2 platform-selector-card__alert">
            <span><strong>Privacy:</strong> Your data export is processed on your device and is never sent to any server.</span>
          </v-alert>

          <v-row class="platform-options-grid mb-6">
            <v-col v-for="platform in platforms" :key="platform.id" cols="6" sm="4" class="pa-2">
              <v-btn
                block
                depressed
                large
                :color="selectedPlatformId === platform.id ? 'primary' : 'grey lighten-3'"
                :dark="selectedPlatformId === platform.id"
                :class="['pa-4 platform-selector-button', { 'platform-selector-button--selected': selectedPlatformId === platform.id }]"
                @click="selectPlatform(platform.id)"
              >
                <div class="d-flex flex-column align-center">
                  <DiscordIcon
                    v-if="platform.id === 'discord'"
                    size="28px"
                    margin-right="0"
                    :color="selectedPlatformId === platform.id ? 'white' : 'var(--v-secondary-base)'"
                    class="mb-1"
                  />
                  <v-icon v-else size="28" class="mb-1" :color="selectedPlatformId === platform.id ? 'white' : 'secondary'">{{ platform.icon }}</v-icon>
                  <span class="text-body-2 font-weight-medium text-center">{{ platform.name }}</span>
                </div>
              </v-btn>
            </v-col>
          </v-row>
        </v-card-text>

        <v-card-actions class="pa-4 pt-2">
          <v-spacer></v-spacer>
          <v-btn text rounded @click="closeDialog">Cancel</v-btn>
          <v-btn color="primary" rounded depressed :disabled="!selectedPlatformId" @click="proceedToUpload">Continue<v-icon right>mdi-arrow-right</v-icon></v-btn>
        </v-card-actions>
      </template>

      <!-- Step 2: File Upload (delegated to ImportZone with platform info) -->
      <div v-if="step === 'file-upload'" class="pa-0">
        <ImportZone :selectedPlatform="selectedPlatformId" @close="closeDialog" @success="handleUploadSuccess" />
      </div>
    </v-card>

  </v-dialog>
</template>

<script>
import { PLATFORM_METADATA } from '../../utils/uploadFormUtils.js'
import DiscordIcon from '../DiscordIcon.vue'
import ImportZone from './ImportZone.vue'

export default {
  name: 'PlatformSelector',
  components: {
    DiscordIcon,
    ImportZone,
  },
  data() {
    return {
      dialog: false,
      step: 'platform-selection',
      selectedPlatformId: null,
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
      this.finalizeUpload()
    },
    finalizeUpload() {
      this.$emit('success')
      this.closeDialog()
    },
  },
}
</script>

<style scoped lang="scss">
.platform-selector-button {
  min-height: 96px;
  text-transform: none;
  letter-spacing: normal;
  white-space: normal;
  line-height: 1.2;
  border-radius: 4px !important;
  border: 1px solid #d6d6d6 !important;

  &:hover {
    border-color: var(--v-primary-lighten3) !important;
  }

  &--selected {
    border-color: var(--v-primary-base) !important;
  }
}

.platform-selector-card {
  border-radius: 18px;
}

.platform-options-grid {
  margin-left: -8px;
  margin-right: -8px;
}
</style>

