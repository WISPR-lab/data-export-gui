<!--
Enhanced Upload Form for Platform Data Exports (ZIP files)

This component handles ZIP file uploads from various data export platforms.
It replaces the generic UploadForm for the new workflow.
-->
<template>
  <span>
    <!-- Progress Dialog -->
    <import-progress
      :open.sync="isUploading"
      :progress="percentCompleted"
      :status-message="statusMessage"
    ></import-progress>

    <!-- Main Upload Dialog -->
    <v-dialog v-model="dialog" persistent max-width="500px">
      <v-card>
        <v-card-title class="pb-2">
          <DiscordIcon v-if="selectedPlatform === 'discord'" size="20px" margin-right="12px" fill="var(--v-primary-base)" />
          <v-icon v-else color="primary" class="mr-3">{{ platformIcon }}</v-icon>
          <span class="headline font-weight-medium">Import {{ platformName }} Data</span>
        </v-card-title>
        
        <v-card-text class="pb-0">
          <!-- Error & Warning Display -->
          <import-error-display
            :error-type="uploadErrorType"
            :errors="uploadErrors"
            :warnings="uploadWarnings"
            :local-errors="localErrors"
          ></import-error-display>

          <v-alert dense text type="success" icon="mdi-information" class="mb-4">
            This tool is limited to the data provided by {{ platformName }}. For example, platforms may record incorrect time or location of events.
          </v-alert>

          <!-- File Upload -->
          <div
            class="upload-dropzone mb-2"
            :class="{
              'upload-dropzone--dragging': isDragging,
              'upload-dropzone--filled': !!selectedFile,
            }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="onDrop"
            @click="!selectedFile && $refs.fileInput.click()"
          >
            <template v-if="!selectedFile">
              <div class="upload-dropzone__badge mb-3">
                <v-icon size="24" color="primary">mdi-tray-arrow-up</v-icon>
              </div>
              <p class="text-body-2 font-weight-medium mb-1">Drag and drop your ZIP file here</p>
              <p class="text-caption text--secondary mb-3">or</p>
              <v-btn outlined rounded small color="primary" @click.stop="$refs.fileInput.click()">
                Browse Files
              </v-btn>
            </template>
 
            <template v-else>
              <div class="upload-dropzone__badge upload-dropzone__badge--success mb-3">
                <v-icon size="24" color="success">mdi-file-check-outline</v-icon>
              </div>
              <p class="text-body-2 font-weight-medium mb-0">{{ selectedFile.name }}</p>
              <p class="text-caption text--secondary mb-3">{{ formatFileSize(selectedFile.size) }}</p>
              <v-btn text rounded x-small color="error" @click.stop="clearFile">
                Remove
              </v-btn>
            </template>
 
            <input
              ref="fileInput"
              type="file"
              accept=".zip"
              class="d-none"
              @change="onInputChange"
            />
          </div>

          <p class="text-body2 text--secondary mb-4">
            Don't have your export yet?
            <router-link to="/how-to-request" target="_blank" class="font-weight-medium">
              View step-by-step instructions
            </router-link>
          </p>

          <!-- Timeline Name -->
          <div class="mb-4" v-if="selectedFile">
            <v-text-field
              v-model="dataExportName"
              label="Data Export Name"
              outlined
              dense
              required
              :rules="nameRules"
              placeholder="e.g. My Data Export"
            ></v-text-field>
          </div>
        </v-card-text>

        <v-divider></v-divider>

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
import ImportProgress from './Progress.vue';
import ImportErrorDisplay from './ErrorDisplay.vue';
import DiscordIcon from '../DiscordIcon.vue';
import {
  getPlatformName,
  getPlatformIcon,
  validateFile,
  formatFileSize,
  stripZipExtension,
} from '../../utils/uploadFormUtils.js';

export default {
  name: 'ImportZone',
  components: {
    ImportProgress,
    ImportErrorDisplay,
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
      dataExportName: '',
      nameRules: [
        (v) => !!v || 'Data export name is required',
        (v) => (v && v.length <= 255) || 'Name must be less than 255 characters',
      ],
      localErrors: [],
      fileValid: false,
      isDragging: false,
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
        this.dataExportName.trim().length > 0 &&
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
    this.suggestDEName();
  },
  methods: {
    onDrop(event) {
      this.isDragging = false;
      const file = event.dataTransfer && event.dataTransfer.files[0];
      if (file) {
        this.processFile(file);
      }
    },
    onInputChange(event) {
      const file = event.target.files && event.target.files[0];
      if (file) {
        this.processFile(file);
      }
      // reset so selecting the same file again still fires @change
      event.target.value = '';
    },
    processFile(file) {
      this.selectedFile = file;
      this.localErrors = [];
      this.fileValid = false;
 
      const validation = validateFile(file);
      this.localErrors = validation.errors;
      this.fileValid = validation.valid;
 
      if (this.fileValid) {
        this.dataExportName = stripZipExtension(file.name);
      }
    },
    clearFile() {
      this.selectedFile = null;
      this.dataExportName = '';
      this.fileValid = false;
      this.localErrors = [];
    },
    async suggestDEName() {
      // Python extractor auto-generates names on upload
      // Just use platform name as placeholder
      if (!this.dataExportName || this.dataExportName === '') {
        this.dataExportName = this.selectedPlatform;
      }
    },
    async submitUpload() {
      if (!this.canSubmit) {
        return;
      }

      const projectId = this.$store.state.project.id;
      if (!projectId) {
        this.localErrors.push('No active project found');
        return;
      }

      try {
        await processUpload(
          this.selectedFile,
          this.selectedPlatform,
          this.dataExportName,
          projectId,
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

.upload-dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 48px 16px;
  border: 2px dashed rgba(0, 0, 0, 0.18);
  border-radius: 16px;
  background-color: rgba(0, 0, 0, 0.015);
  transition: border-color 0.15s, background-color 0.15s, transform 0.15s;
  cursor: pointer;

  &:hover {
    border-color: rgba(25, 118, 210, 0.4);
    background-color: rgba(25, 118, 210, 0.03);
  }
 
  &--dragging {
    border-color: var(--v-primary-base);
    background-color: rgba(25, 118, 210, 0.06);
    transform: scale(1.01);
  }
 
  &--filled {
    border-style: solid;
    border-color: rgba(0, 0, 0, 0.1);
    background-color: rgba(0, 0, 0, 0.015);
    cursor: default;
  }
 
  &__badge {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background-color: rgba(25, 118, 210, 0.1);
 
    &--success {
      background-color: rgba(76, 175, 80, 0.12);
    }
  }
}
 
:deep(.v-application--dark) .upload-dropzone {
  border-color: rgba(255, 255, 255, 0.22);
  background-color: rgba(255, 255, 255, 0.02);
 
  &--filled {
    border-color: rgba(255, 255, 255, 0.12);
  }
}
</style>
