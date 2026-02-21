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
          <span>Import {{ platformName }} Data</span>
          <v-spacer></v-spacer>
          <v-btn icon small @click="closeDialog">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-divider></v-divider>

        <v-card-text class="pa-6">
          <!-- Platform Info Section -->
          <div class="mb-6">
            <div class="d-flex align-center mb-4">
              <v-icon size="48" color="primary" class="mr-4">{{ platformIcon }}</v-icon>
              <div>
                <h3 class="text-body1 font-weight-medium">Upload your {{ platformName }} data export</h3>
              </div>
            </div>
          </div>

          <!-- Instructions -->
          <v-alert outlined type="info" class="mb-6">
            <h4 class="text-body2 font-weight-medium mb-2">Before you upload:</h4>
            <ul class="text-body2 mb-0">
              <li>Make sure you've downloaded the ZIP file from {{ platformName }}</li>
              <li>The file should contain the exported data structure exactly as downloaded</li>
              <li>Do not modify or extract files from the ZIP before uploading</li>
            </ul>
          </v-alert>

          <!-- Need Help Link -->
          <div class="mb-6 pa-4 bg-blue-lighten rounded">
            <div class="d-flex align-center">
              <v-icon small class="mr-2">mdi-help-circle-outline</v-icon>
              <span class="text-body2">
                Unsure how to get this data?
                <router-link to="/how-to-request" target="_blank" class="font-weight-medium">
                  View our step-by-step guide
                </router-link>
              </span>
            </div>
          </div>

          <!-- Error & Warning Display -->
          <upload-error-display
            :error-type="uploadErrorType"
            :errors="uploadErrors"
            :warnings="uploadWarnings"
            :local-errors="localErrors"
          ></upload-error-display>

          <!-- File Upload -->
          <div class="mb-6">
            <v-file-input
              v-model="selectedFile"
              label="Choose ZIP file"
              outlined
              dense
              accept=".zip"
              prepend-icon="mdi-file-archive"
              show-size
              @change="handleFileSelected"
              @click:clear="clearFile"
            ></v-file-input>
          </div>

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

          <!-- File Info Summary -->
          <div v-if="selectedFile && fileValid" class="mb-6 pa-4 bg-green-lighten rounded">
            <div class="d-flex align-center">
              <v-icon small color="success" class="mr-2">mdi-check-circle</v-icon>
              <div class="text-body2">
                <strong>Ready to import:</strong>
                <br />
                {{ selectedFile.name }} ({{ formatFileSize(selectedFile.size) }})
              </div>
            </div>
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
        this.closeDialog();
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
.bg-blue-lighten {
  background-color: #e3f2fd;
}

.bg-green-lighten {
  background-color: #e8f5e9;
}

// Dark mode support
:deep(.v-application--dark) {
  .bg-blue-lighten {
    background-color: #1a237e;
  }

  .bg-green-lighten {
    background-color: #1b5e20;
  }
}
</style>
