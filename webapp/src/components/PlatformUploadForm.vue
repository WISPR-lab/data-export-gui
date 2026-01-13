<!--
Enhanced Upload Form for Platform Data Exports (ZIP files)

This component handles ZIP file uploads from various data export platforms.
It replaces the generic UploadForm for the new workflow.
-->
<template>
  <span>
    <!-- Progress Dialog -->
    <v-dialog v-model="isUploading" persistent width="700">
      <v-card flat class="pa-5">
        <h3 class="mb-4">Processing Your Data Export...</h3>
        <br />
        <v-progress-linear
          color="primary"
          height="25"
          :value="percentCompleted"
        >
          {{ percentCompleted }}%
        </v-progress-linear>
        <v-divider class="my-4"></v-divider>
        <p class="text-body2 text-muted">
          {{ statusMessage }}
        </p>
      </v-card>
    </v-dialog>

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
                <!-- <p class="text-caption text-muted mb-0">ZIP file from {{ platformName }} Takeout/Data Download</p> -->
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

          <!-- Error Display -->
          <div v-if="errors.length > 0" class="mb-6">
            <v-alert v-for="(error, index) in errors" :key="index" outlined type="error" class="mb-2">
              {{ error }}
            </v-alert>
          </div>

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
            <!-- Debug: Upload Sample Data Button -->
            <v-btn small color="secondary" class="mt-2" @click="uploadSampleData">
              <v-icon left small>mdi-database-import</v-icon>
              Upload Sample Data (Debug)
            </v-btn>
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
              hint="Choose a descriptive name for this analysis"
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

import BrowserDB from '../database.js'
import { samplePlatformData, pushSampleEventsToDB } from './samplePlatformData.js'

export default {
  name: 'PlatformUploadForm',
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
      isUploading: false,
      percentCompleted: 0,
      statusMessage: 'Validating file...',
      errors: [],
      fileValid: false,
      platforms: {
        google: { name: 'Google Takeout', icon: 'mdi-google' },
        discord: { name: 'Discord', icon: 'mdi-discord' },
        apple: { name: 'Apple Data', icon: 'mdi-apple' },
        facebook: { name: 'Facebook/Meta', icon: 'mdi-facebook' },
        instagram: { name: 'Instagram', icon: 'mdi-instagram' },
        snapchat: { name: 'Snapchat', icon: 'mdi-snapchat' },
      },
    }
  },
  computed: {
    platformName() {
      const platform = this.platforms[this.selectedPlatform]
      return platform ? platform.name : 'Unknown Platform'
    },
    platformIcon() {
      const platform = this.platforms[this.selectedPlatform]
      return platform ? platform.icon : 'mdi-package'
    },
    canSubmit() {
      return this.selectedFile && this.fileValid && this.timelineName.trim().length > 0
    },
  },
  methods: {
    handleFileSelected(file) {
      this.errors = []
      this.fileValid = false

      if (!file) {
        return
      }

      // Validate file type
      if (!file.name.toLowerCase().endsWith('.zip')) {
        this.errors.push('Please select a ZIP file')
        return
      }

      // Validate file size (max 5GB)
      const maxSize = 5 * 1024 * 1024 * 1024
      if (file.size > maxSize) {
        this.errors.push('File size exceeds 5GB limit')
        return
      }

      // TODO: Add ZIP validation here
      // - Verify ZIP structure
      // - Check for expected platform directories
      // - Validate against platform schema

      this.fileValid = true
      this.timelineName = file.name.replace(/\.zip$/i, '')
    },
    async uploadSampleData() {
      // Debug: Upload sample data directly to the database
      try {
        this.isUploading = true;
        this.statusMessage = 'Uploading sample data...';
        this.percentCompleted = 0;
        // Simulate progress
        for (let i = 0; i <= 100; i += 25) {
          this.percentCompleted = i;
          await new Promise(r => setTimeout(r, 150));
        }
        // Actually upload sample events
        await pushSampleEventsToDB();
        // Force UI to reload sketch/timelines so new timeline appears
        if (this.$store && this.$store.dispatch && this.$store.state.sketch && this.$store.state.sketch.id) {
          await this.$store.dispatch('updateSketch', this.$store.state.sketch.id);
        }
        this.statusMessage = 'Sample data uploaded!';
        this.isUploading = false;
        // Prompt for timeline metadata editing (emit event or set flag)
        this.$emit('edit-timeline-metadata', {
          name: samplePlatformData.name,
          provider: samplePlatformData.provider,
          context: samplePlatformData.context,
          total_file_size: samplePlatformData.total_file_size,
          sketch_id: samplePlatformData.sketch_id,
        });
      } catch (e) {
        this.errors.push('Sample data upload failed: ' + (e.message || e));
        console.error(e);
        this.isUploading = false;
      }
    },
    clearFile() {
      this.selectedFile = null
      this.timelineName = ''
      this.fileValid = false
      this.errors = []
    },
    async submitUpload() {
      if (!this.canSubmit) {
        return
      }

      this.isUploading = true
      this.percentCompleted = 0
      this.errors = []

      try {
        // TODO: Implement actual ZIP processing logic here
        // Steps:
        // 1. Read ZIP file
        // 2. Validate against platform schema
        // 3. Extract relevant files
        // 4. Parse files and create events/states
        // 5. Store in database
        // 6. Navigate to analysis view

        // For now, simulate the process
        await this.simulateUploadProcess()

        // Emit success event
        this.$emit('success')
        this.closeDialog()
      } catch (error) {
        this.errors.push(error.message || 'An error occurred during upload')
        this.isUploading = false
      }
    },
    simulateUploadProcess() {
      return new Promise((resolve) => {
        const steps = [
          'Validating ZIP file structure...',
          'Checking against platform schema...',
          'Extracting data files...',
          'Parsing events and activities...',
          'Creating timeline entries...',
          'Storing in database...',
        ]

        let currentStep = 0
        const interval = setInterval(() => {
          currentStep++
          this.percentCompleted = Math.floor((currentStep / (steps.length + 1)) * 100)
          if (currentStep < steps.length) {
            this.statusMessage = steps[currentStep]
          } else {
            clearInterval(interval)
            this.statusMessage = 'Complete!'
            this.isUploading = false
            resolve()
          }
        }, 800)
      })
    },
    formatFileSize(bytes) {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
    },
    closeDialog() {
      this.dialog = false
      this.$emit('close')
    },
  },
}
</script>

<style scoped lang="scss">
.text-muted {
  color: rgba(0, 0, 0, 0.54);
}

.bg-blue-lighten {
  background-color: #e3f2fd;
}

.bg-green-lighten {
  background-color: #e8f5e9;
}

// Dark mode support
:deep(.v-application--dark) {
  .text-muted {
    color: rgba(255, 255, 255, 0.54);
  }

  .bg-blue-lighten {
    background-color: #1a237e;
  }

  .bg-green-lighten {
    background-color: #1b5e20;
  }
}
</style>
