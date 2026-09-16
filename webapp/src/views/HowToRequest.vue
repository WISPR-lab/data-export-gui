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
          @click="selectPlatform(platform.id)"
          class="platform-btn"
          large
        >
          {{ platform.name }}
        </v-btn>
      </div>

      <v-divider class="mb-10"></v-divider>

      <!-- Steps -->
      <div v-if="selectedPlatform.comingSoon" class="text-center pa-8">
        <h2 class="text-h5 font-weight-light">Coming Soon</h2>
        <p class="text-body1 text-disabled mt-2">Instructions for {{ selectedPlatform.name }} are not yet available.</p>
      </div>

      <div v-else>
        <!-- Top Security & Access Alert -->
        <v-alert type="warning" text class="mb-8 font-weight-medium">
          Requesting an export sends a security alert to this email account. If someone else is logged into your account or has access to your password and/or 2FA methods, they will be notified and able to view or download the data.
        </v-alert>

        <v-timeline align-top dense class="px-0">
          <v-timeline-item
            v-for="(step, index) in displayedSteps"
            :key="index"
            color="primary"
            fill-dot
            small
            class="mb-10"
          >
            <template v-slot:icon>
              <span class="white--text font-weight-bold" style="font-size: 13px;">{{ index + 1 }}</span>
            </template>

            <v-row class="align-start">
              <v-col cols="12" md="7" class="pr-md-8">
                <h2 class="text-h5 font-weight-medium mb-3">{{ step.title }}</h2>

                <div v-if="step.link" class="mb-3">
                  <a :href="step.link.url" target="_blank" rel="noopener noreferrer" class="primary--text">
                    {{ step.link.text }}
                    <v-icon x-small>mdi-open-in-new</v-icon>
                  </a>
                </div>

                <div v-if="step.description && typeof step.description === 'string'" 
                    class="text-body-1 markdown-description"
                    v-html="renderMarkdown(step.description)">
                </div>

                <div v-if="step.alert" class="mt-4" style="max-width: 100%;">
                  <v-alert :type="step.alert.type || 'warning'" text dense class="font-weight-medium">
                    <span v-html="renderMarkdown(step.alert.text)"></span>
                  </v-alert>
                </div>

                <!-- Generic Orange Sensitive Data Alert inside final step block -->
                <div v-if="index === displayedSteps.length - 1" class="mt-4" style="max-width: 100%;">
                  <v-alert type="warning" text class="font-weight-medium mb-0">
                    This export contains your sensitive information. Treat it as securely as you would a password or financial records.
                  </v-alert>
                </div>
              </v-col>

              <v-col v-if="step.image || step.images" cols="12" md="5" class="pt-0 pt-md-3">
                <v-img 
                  v-if="step.image"
                  :src="step.image" 
                  :alt="step.title" 
                  class="rounded-lg elevation-2"
                  max-width="450"
                  contain
                />
                <template v-if="step.images">
                  <v-img 
                    v-for="(img, imgIdx) in step.images"
                    :key="imgIdx"
                    :src="img" 
                    :alt="step.title" 
                    class="rounded-lg elevation-2 mb-3"
                    max-width="450"
                    contain
                  />
                </template>
              </v-col>
            </v-row>
          </v-timeline-item>
        </v-timeline>
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

<script>
import PageHeader from '../components/Navigation/PageHeader.vue'
import { marked } from 'marked'
import { instructionRegistry } from '@/constants/request_instructions'

export default {
  name: 'HowToRequest',
  components: { PageHeader },
  data() {
    const routeKey = (this.$route.hash ? this.$route.hash.replace('#', '') : null) || this.$route.query.platform || this.$route.query.tab;
    const initialPlatform = (routeKey && instructionRegistry[routeKey]) ? instructionRegistry[routeKey] : instructionRegistry.google;
    return {
      instructionRegistry,
      selectedPlatform: initialPlatform,
      platforms: Object.values(instructionRegistry).map(function(platform) {
        return {
          id: platform.id,
          name: platform.name
        };
      })
    };
  },
  watch: {
    '$route'(to) {
      const platformKey = (to.hash ? to.hash.replace('#', '') : null) || to.query.platform || to.query.tab;
      if (platformKey && this.instructionRegistry[platformKey]) {
        this.selectedPlatform = this.instructionRegistry[platformKey];
      }
    }
  },
  mounted() {
    window.scrollTo({ top: 0 });
  },
  computed: {
    displayedSteps() {
      return this.selectedPlatform && this.selectedPlatform.steps ? this.selectedPlatform.steps : [];
    }
  },
  methods: {
    selectPlatform(platformId) {
      if (this.instructionRegistry[platformId]) {
        this.selectedPlatform = this.instructionRegistry[platformId];
        this.$router.replace({
          name: 'HowToRequest',
          query: { tab: platformId }
        }).catch(function() {});
      }
    },
    renderMarkdown(text) {
      if (!text) return '';
      return marked.parse(text);
    }
  }
};
</script>

<style scoped lang="scss">

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

</style>