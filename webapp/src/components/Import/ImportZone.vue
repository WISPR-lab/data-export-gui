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
      <v-card rounded="lg">
        <v-card-title class="text-h6 font-weight-medium pb-2">
          <DiscordIcon v-if="selectedPlatform === 'discord'" size="20px" margin-right="12px" fill="currentColor" />
          <v-icon v-else color="secondary" class="mr-3">{{ platformIcon }}</v-icon>
          <span class="text-h6 font-weight-medium">Import {{ platformName }} Data</span>
        </v-card-title>
        
        <v-card-text class="pb-0 pt-1">
          <p class="text-body-2 text--secondary mb-4">
            Don't have your export yet?
            <router-link to="/how-to-request" target="_blank" class="font-weight-medium">
              View instructions
            </router-link>
          </p>

          <v-alert dense text type="info" class="mb-4 text-body-2">
            This tool is limited to the data provided by {{ platformName }}.
            For example, platforms may record incorrect time or location of events.
            Verify all results.
          </v-alert>

          <v-alert v-if="memorySamplingEnabled" dense text type="warning" class="mb-4 text-body-2">
            PERFORMANCE MEMORY TRACKING: ON — this run will be ~5-10% slower and a
            <code>_mem_perf.csv</code> will download automatically when it finishes.
          </v-alert>

          <v-alert v-if="allowMultipleFiles" dense text type="info" class="mb-4 text-body-2">
            Apple often splits your export into multiple ZIP files — you can select or drop them all here at once.
          </v-alert>

          <!-- <v-card-text class="pb-0 pt-1">
          <v-alert dense text type="info" class="mb-4 text-body-2">
            Don't have your export yet?
            <router-link to="/how-to-request" target="_blank" class="font-weight-medium">
              View instructions
            </router-link>
          </v-alert>

          <p class="text-body-2 text--secondary mb-4">
            This tool is limited to the data provided by {{ platformName }}. 
            For example, platforms may record incorrect time or location of events.
            Verify all results.
          </p> -->

          <!-- File Upload -->
          <div
            class="upload-dropzone mb-2"
            :class="{
              'upload-dropzone--dragging': isDragging,
              'upload-dropzone--filled': hasFiles,
            }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="onDrop"
            @click="(!hasFiles || allowMultipleFiles) && $refs.fileInput.click()"
          >
            <template v-if="!hasFiles">
              <div class="upload-dropzone__badge mb-3">
                <v-icon size="24" color="primary">mdi-tray-arrow-up</v-icon>
              </div>
              <p class="text-body-2 font-weight-medium mb-1">
                Drag and drop your ZIP file{{ allowMultipleFiles ? 's' : '' }} here
              </p>
              <p class="text-caption text--secondary mb-3">or</p>
              <v-btn outlined rounded small color="primary" @click.stop="$refs.fileInput.click()">
                Browse Files
              </v-btn>
            </template>

            <template v-else>
              <div class="upload-dropzone__badge upload-dropzone__badge--success mb-3">
                <v-icon size="24" color="success">mdi-file-check-outline</v-icon>
              </div>
              <div
                v-for="(file, idx) in selectedFiles"
                :key="file.name + idx"
                class="upload-dropzone__file d-flex align-center justify-center mb-1"
                @click.stop
              >
                <span class="text-body-2 font-weight-medium">{{ file.name }}</span>
                <span class="text-caption text--secondary mx-2">{{ formatFileSize(file.size) }}</span>
                <v-btn text rounded x-small color="error" @click.stop="removeFile(idx)">
                  Remove
                </v-btn>
              </div>
              <v-btn
                v-if="allowMultipleFiles"
                outlined
                rounded
                small
                color="primary"
                class="mt-2"
                @click.stop="$refs.fileInput.click()"
              >
                Add Another ZIP
              </v-btn>
            </template>

            <input
              ref="fileInput"
              type="file"
              accept=".zip"
              :multiple="allowMultipleFiles"
              class="d-none"
              @change="onInputChange"
            />
          </div>

          <!-- Error & Warning Display -->
          <import-error-display
            class="mt-4"
            :error-type="uploadErrorType"
            :errors="uploadErrors"
            :warnings="uploadWarnings"
            :local-errors="localErrors"
          ></import-error-display>


          <!-- Timeline Name -->
          <div class="mb-4" v-if="hasFiles">
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
          <v-btn text rounded @click="closeDialog">
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            rounded
            depressed
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
  platformAllowsMultipleFiles,
  validateFile,
  formatFileSize,
  stripZipExtension,
} from '../../utils/uploadFormUtils.js';
import { loadConfig } from '../../utils/config.js';

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
      selectedFiles: [],
      dataExportName: '',
      nameRules: [
        (v) => !!v || 'Data export name is required',
        (v) => (v && v.length <= 255) || 'Name must be less than 255 characters',
      ],
      localErrors: [],
      fileValid: false,
      isDragging: false,
      memorySamplingEnabled: false,
    };
  },
  computed: {
    platformName() {
      return getPlatformName(this.selectedPlatform);
    },
    platformIcon() {
      return getPlatformIcon(this.selectedPlatform);
    },
    allowMultipleFiles() {
      return platformAllowsMultipleFiles(this.selectedPlatform);
    },
    hasFiles() {
      return this.selectedFiles.length > 0;
    },
    canSubmit() {
      return (
        this.hasFiles &&
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
  async mounted() {
    this.suggestDEName();
    try {
      const config = await loadConfig();
      this.memorySamplingEnabled = !!(config.performance && config.performance.memory_sampling_enabled);
    } catch (e) {
      // Config load failures shouldn't block the upload dialog — just skip the banner.
      this.memorySamplingEnabled = false;
    }
  },
  methods: {
    onDrop(event) {
      this.isDragging = false;
      const files = event.dataTransfer && Array.from(event.dataTransfer.files || []);
      if (files && files.length) {
        this.processFiles(files);
      }
    },
    onInputChange(event) {
      const files = event.target.files && Array.from(event.target.files);
      if (files && files.length) {
        this.processFiles(files);
      }
      // reset so selecting the same file again still fires @change
      event.target.value = '';
    },
    processFiles(files) {
      const incoming = this.allowMultipleFiles ? files : [files[0]];
      this.selectedFiles = this.allowMultipleFiles
        ? [...this.selectedFiles, ...incoming]
        : incoming;
      this.localErrors = [];
      this.fileValid = false;

      const errors = this.selectedFiles.flatMap((f) => validateFile(f).errors);
      this.localErrors = errors;
      this.fileValid = errors.length === 0;

      if (this.fileValid) {
        this.dataExportName = stripZipExtension(this.selectedFiles[0].name);
      }
    },
    removeFile(idx) {
      this.selectedFiles.splice(idx, 1);
      if (!this.hasFiles) {
        this.clearFile();
        return;
      }
      const errors = this.selectedFiles.flatMap((f) => validateFile(f).errors);
      this.localErrors = errors;
      this.fileValid = errors.length === 0;
    },
    clearFile() {
      this.selectedFiles = [];
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
        const filesArg = this.allowMultipleFiles ? this.selectedFiles : this.selectedFiles[0];
        await processUpload(
          filesArg,
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
  border: 2px dashed #e0e0e0;
  border-radius: 4px;
  background-color: rgba(0, 0, 0, 0.015);
  transition: border-color 0.15s, background-color 0.15s, transform 0.15s;
  cursor: pointer;

  &:hover {
    border-color: var(--v-primary-lighten3);
    background-color: rgba(25, 118, 210, 0.03);
  }
 
  &--dragging {
    border-color: var(--v-primary-base);
    background-color: rgba(25, 118, 210, 0.06);
    transform: scale(1.01);
  }
 
  &--filled {
    border-style: solid;
    border-color: #e0e0e0;
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

  &__file {
    flex-wrap: wrap;
  }
}

:deep(.v-application--dark) .upload-dropzone {
  border-color: rgba(255, 255, 255, 0.18);
  background-color: rgba(255, 255, 255, 0.02);
 
  &--filled {
    border-color: rgba(255, 255, 255, 0.14);
  }
}
</style>
