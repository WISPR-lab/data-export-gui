<template>
  <div>
    <PageHeader />
    <v-divider></v-divider>

    <v-container class="pa-8" style="max-width: 1400px;">
      <h1 class="text-h3 mb-8 mt-8 font-weight-light">How to Request Your Data Exports</h1>

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
          <div class="d-flex align-start">
            <div class="step-content">
              <div class="d-flex align-start gap-4">
                <div class="step-number">{{ index + 1 }}</div>
                <div>
                  <h2 class="text-h5 font-weight-medium mb-2">{{ step.title }}</h2>

                  <div v-if="step.link" class="mb-3">
                    <a :href="step.link.url" target="_blank" rel="noopener noreferrer" class="primary--text">
                      {{ step.link.text }}
                      <v-icon x-small>mdi-open-in-new</v-icon>
                    </a>
                  </div>

                  <div v-if="step.description && typeof step.description === 'string'" 
                      class="text-body1 markdown-description"
                      v-html="renderMarkdown(step.description)">
                  </div>

                  <div v-if="step.alert" class="mt-4" style="max-width: 100%;">
                    <v-alert :type="step.alert.type || 'warning'" dense class="font-weight-medium">
                      <span v-html="renderMarkdown(step.alert.text)"></span>
                    </v-alert>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="step.image" class="step-image-col">
              <img 
                :src="`/${step.image}`" 
                :alt="step.title" 
                class="step-image"
              />
            </div>
          </div>

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

<<script>
import PageHeader from '../components/Navigation/PageHeader.vue'
import yaml from 'js-yaml';
import { marked } from 'marked';

export default {
  name: 'HowToRequest',
  components: { PageHeader },
  data() {
    return {
      selectedPlatform: null,
      // Metadata only - Content is loaded from YAML
      platforms: [
        { id: 'google', name: 'Google' },
        { id: 'discord', name: 'Discord' },
        { id: 'apple', name: 'Apple' },
        { id: 'facebook', name: 'Facebook / Instagram' },
        { id: 'snapchat', name: 'Snapchat' }
      ]
    }
  },
  computed: {
    displayedSteps() {
      // Returns the steps from the loaded data
      return this.selectedPlatform && this.selectedPlatform.steps ? this.selectedPlatform.steps : []
    },
  },
  watch: {
    // Watch for tab clicks to load data
    'selectedPlatform.id': {
      immediate: true,
      handler(newId) {
        if (newId) this.loadPlatformData(newId);
      }
    }
  },
  mounted() {
    // Initialize with Google
    this.selectedPlatform = this.platforms[0];
  },
  methods: {
    async loadPlatformData(id) {
      try {
        // Fetch from public/how2request/[id].yaml
        const response = await fetch(`/how2request/text/${id}_instr.yaml`);
        if (!response.ok) throw new Error('File not found');
        
        const text = await response.text();
        
        // Prevent loading HTML 404 pages
        if (text.trim().startsWith('<!DOCTYPE')) return;

        // Parse YAML and merge with ID/Name
        const data = yaml.load(text);
        
        // Update selectedPlatform with the full data (steps, icons, etc.)
        this.selectedPlatform = {
          ...this.platforms.find(p => p.id === id),
          ...data
        };
      } catch (e) {
        console.error(`Error loading ${id}:`, e);
      }
    },
    renderMarkdown(text) {
      if (!text) return '';
      return marked.parse(text);
    }
  }
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
  flex: 1.5;
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