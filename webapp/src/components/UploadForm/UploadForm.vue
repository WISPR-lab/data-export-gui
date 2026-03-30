<!--
Enhanced Upload Form for Platform Data Exports (ZIP files)

This component handles ZIP file uploads from various data export platforms.
It replaces the generic UploadForm for the new workflow.
-->
<template>
  <span>
    <!-- Progress Dialog -->
    <upload-progress-dialog
      :open.sync="isUploading"
      :progress="percentCompleted"
      :status-message="statusMessage"
    ></upload-progress-dialog>

    <!-- Main Upload Dialog -->
    <v-dialog v-model="dialog" persistent max-width="700px">
      <v-card>
        <v-card-title class="pb-2">
          <DiscordIcon v-if="selectedPlatform === 'discord'" size="20px" margin-right="12px" fill="var(--v-primary-base)" />
          <v-icon v-else color="primary" class="mr-3">{{ platformIcon }}</v-icon>
          <span>Import {{ platformName }} Data</span>
          <v-spacer></v-spacer>
          <v-btn icon small @click="closeDialog">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-divider></v-divider>

        <v-card-text class="pa-6">

          <!-- Need Help Link -->
          <v-alert dense text type="info" class="mb-5">
            Don't have your export yet?
            <router-link to="/how-to-request" target="_blank" class="font-weight-medium">
              View step-by-step instructions
            </router-link>
          </v-alert>

          <!-- Error & Warning Display -->
          <upload-error-display
            :error-type="uploadErrorType"
            :errors="uploadErrors"
            :warnings="uploadWarnings"
            :local-errors="localErrors"
          ></upload-error-display>

          <!-- File Upload -->
          <div class="mb-4">
            <v-file-input
              v-model="selectedFile"
              label="Choose ZIP file"
              outlined
              dense
              accept=".zip"
              prepend-inner-icon="mdi-file-archive"
              prepend-icon=""
              show-size
              @change="handleFileSelected"
              @click:clear="clearFile"
            ></v-file-input>
          </div>

          <!-- File Ready Confirmation -->
          <v-alert v-if="selectedFile && fileValid" dense text type="success" class="mb-4">
            <strong>{{ selectedFile.name }}</strong> &mdash; {{ formatFileSize(selectedFile.size) }}
          </v-alert>

          <!-- Timeline Name Input (appears after file selection) -->
          <div v-if="selectedFile" class="mb-6">
            <v-text-field
              v-model="timelineName"
              label="Timeline Name"
              outlined
              dense
              :placeholder="`e.g., '${platformName} Data Export'`"
              :rules="nameRules"
              counter="255"
              hint="Choose a descriptive name for this data export file"
              persistent-hint
            ></v-text-field>
          </div>


        </v-card-text>

        <!-- Action Buttons -->
        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn text @click="closeDialog">
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            :disabled="!canSubmit"
            @click="submitUpload"
            :loading="isUploading"
          >
            <v-icon left>mdi-upload</v-icon>
            Import Data
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </span>
</template>

<script>
import { processUpload } from '../../upload.js';
import UploadProgressDialog from './ProgressDialog.vue';
import UploadErrorDisplay from './UploadErrorDisplay.vue';
import DiscordIcon from '../DiscordIcon.vue';
import {
  getPlatformName,
  getPlatformIcon,
  validateFile,
  formatFileSize,
  stripZipExtension,
} from '../../utils/uploadFormUtils.js';

export default {
  name: 'PlatformUploadForm',
  components: {
    UploadProgressDialog,
    UploadErrorDisplay,
    DiscordIcon,
  },
  props: {
    selectedPlatform: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      dialog: true,
      selectedFile: null,
      timelineName: '',
      nameRules: [
        (v) => !!v || 'Timeline name is required',
        (v) => (v && v.length <= 255) || 'Name must be less than 255 characters',
      ],
      localErrors: [],
      fileValid: false,
    };
  },
  computed: {
    platformName() {
      return getPlatformName(this.selectedPlatform);
    },
    platformIcon() {
      return getPlatformIcon(this.selectedPlatform);
    },
    canSubmit() {
      return (
        this.selectedFile &&
        this.fileValid &&
        this.timelineName.trim().length > 0 &&
        !this.isUploading
      );
    },
    isUploading() {
      return this.$store.state.uploadState.isProcessing;
    },
    percentCompleted() {
      return this.$store.state.uploadState.progress;
    },
    statusMessage() {
      return this.$store.state.uploadState.status;
    },
    uploadErrorType() {
      return this.$store.state.uploadState.errorType;
    },
    uploadErrors() {
      return this.$store.state.uploadState.errors;
    },
    uploadWarnings() {
      return this.$store.state.uploadState.warnings;
    },
  },
  watch: {
    statusMessage(newVal) {
      if (newVal === 'complete') {
        this.$emit('success');
        const warnings = this.uploadWarnings || [];
        if (!warnings.length) {
          this.closeDialog();
        }
      }
    },
  },
  mounted() {
    this.suggestTimelineName();
  },
  methods: {
    handleFileSelected(file) {
      this.localErrors = [];
      this.fileValid = false;

      if (!file) {
        return;
      }

      const validation = validateFile(file);
      this.localErrors = validation.errors;
      this.fileValid = validation.valid;

      if (this.fileValid) {
        this.timelineName = stripZipExtension(file.name);
      }
    },
    clearFile() {
      this.selectedFile = null;
      this.timelineName = '';
      this.fileValid = false;
      this.localErrors = [];
    },
    async suggestTimelineName() {
      // Python extractor auto-generates names on upload
      // Just use platform name as placeholder
      if (!this.timelineName || this.timelineName === '') {
        this.timelineName = this.selectedPlatform;
      }
    },
    async submitUpload() {
      if (!this.canSubmit) {
        return;
      }

      const sketchId = this.$store.state.sketch.id;
      if (!sketchId) {
        this.localErrors.push('No active sketch found');
        return;
      }

      try {
        await processUpload(
          this.selectedFile,
          this.selectedPlatform,
          sketchId,
          this.$store
        );
      } catch (error) {
        this.localErrors.push(error.message || 'An error occurred during upload');
      }
    },
    formatFileSize(bytes) {
      return formatFileSize(bytes);
    },
    closeDialog() {
      this.dialog = false;
      this.$emit('close');
    },
  },
};
</script>

<style scoped lang="scss">
// Dark mode support
:deep(.v-application--dark) {
  .text-muted {
    color: rgba(255, 255, 255, 0.54);
  }
}
</style>
