<template>
  <v-app>
    <PageHeader />

    <v-divider></v-divider>

    <!-- Main Content -->
    <v-container max-width="1200px" class="py-12">
      <!-- Hero Section - Two Columns -->
      <v-row class="align-center mb-12">
        <v-col cols="12" md="6">
          <h2 class="text-h4 secondary--text mb-6">
            Discover and review <span class="primary--text font-weight-bold">account security incidents</span> using data exports from your online accounts.

          </h2>
          <p class="text-body1 secondary--text line-height-relaxed">
            LEStrADE is an open-source, browser-based tool that helps end-users uncover security events (i.e., login attempts, password changes) that might 
            indicate an account has been compromised. 
          </p>
        </v-col>
        <v-col cols="12" md="6">
          <!-- Screenshot Placeholder -->
          <v-card class="pa-8" style="min-height: 300px; background: linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%);">
            <div class="d-flex align-center justify-center fill-height">
              <div class="text-center">
                <v-icon size="80" class="mb-4 secondary--text">mdi-image-outline</v-icon>
                <p class="text-body2 secondary--text">Interface screenshot</p>
              </div>
            </div>
          </v-card>
        </v-col>
      </v-row>

      <v-divider class="my-12"></v-divider>

      <!-- How It Works Section (Modified) -->
      <div class="mb-12">
        <h2 class="text-h4 mb-8">How It Works</h2>
        
        <v-row>
          <!-- Step 1 -->
          <v-col cols="12" md="3">
            <v-card class="h-100 pa-6 text-center" outlined>
              <div class="step-number primary--text text-h4 font-weight-medium mb-4">1</div>
              <h3 class="text-body1 font-weight-medium mb-3">Request Data Export</h3>
              <p class="text-body2 secondary--text line-height-relaxed">
                Use our guides to request data exports from the platform(s) you want to investigate.
              </p>
            </v-card>
          </v-col>

          <!-- Step 2 -->
          <v-col cols="12" md="3">
            <v-card class="h-100 pa-6 text-center" outlined>
              <div class="step-number primary--text text-h4 font-weight-medium mb-4">2</div>
              <h3 class="text-body1 font-weight-medium mb-3">Download Safely</h3>
              <p class="text-body2 secondary--text line-height-relaxed">
                Download the ZIP file to a secure, password-protected device or USB drive.
              </p>
            </v-card>
          </v-col>

          <!-- Step 3 -->
          <v-col cols="12" md="3">
            <v-card class="h-100 pa-6 text-center" outlined>
              <div class="step-number primary--text text-h4 font-weight-medium mb-4">3</div>
              <h3 class="text-body1 font-weight-medium mb-3">Import and Analyze</h3>
              <p class="text-body2 secondary--text line-height-relaxed">
                Upload the data export here to visualize timelines and security events.
              </p>
            </v-card>
          </v-col>

          <!-- Action Buttons (instead of Step 4) -->
          <v-col cols="12" md="3">
            <div class="d-flex flex-column h-100 justify-center gap-3">
              <v-btn
                large
                rounded
                color="primary"
                @click="goToSketch"
                class="px-6"
              >
                <v-icon left>mdi-cloud-upload</v-icon>
                Get Started
              </v-btn>
              <v-btn
                large
                outlined
                rounded
                color="primary"
                to="/how-to-request"
                class="px-6"
              >
                <v-icon left>mdi-help-circle-outline</v-icon>
                How to Request Data
              </v-btn>
            </div>
          </v-col>
        </v-row>
      </div>

      <v-divider class="my-12"></v-divider>

      <!-- Two Column Section: Features and Platforms -->
      <v-row class="align-center mb-12">
        <!-- Left: Key Capabilities -->
        <v-col cols="12" md="6">
          <h3 class="text-h5 font-weight-medium mb-6">Key Capabilities</h3>
          <v-list class="transparent">
            <v-list-item dense v-for="feature in features" :key="feature">
              <v-list-item-icon class="mr-3">
                <v-icon small color="primary">mdi-check-circle</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title class="text-body2">{{ feature }}</v-list-item-title>
              </v-list-item-content>
            </v-list-item>
          </v-list>
        </v-col>

        <!-- Right: Platforms and Research -->
        <v-col cols="12" md="6">
          <!-- Supported Platforms Card -->
          <v-card class="pa-6 mb-6 light-highlight">
            <h4 class="text-h6 font-weight-medium mb-4">Supported Platforms</h4>
            <div class="d-flex flex-wrap gap-2">
              <v-chip
                v-for="platform in supportedPlatforms"
                :key="platform.name"
                small
                outlined
              >
                <svg v-if="platform.name === 'Discord'" viewBox="0 0 24 24" style="width:14px;height:14px;margin-right:6px;flex-shrink:0" aria-hidden="true">
                  <path fill="currentColor" d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057.101 18.079.11 18.1.128 18.112a19.9 19.9 0 0 0 5.994 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/>
                </svg>
                <v-icon v-else small left>{{ platform.icon }}</v-icon>
                {{ platform.name }}
              </v-chip>
            </div>
          </v-card>

          <!-- Research/About Card -->
          <v-card class="pa-6 light-highlight">
            <p class="text-caption font-weight-medium primary--text mb-2">ABOUT THIS TOOL</p>
            <p class="text-body2 secondary--text mb-0">
              This tool operationalizes findings from the research paper 
              <router-link to="#" class="primary--text font-weight-medium">
                "Hidden in Plain Bytes"
              </router-link>
              which demonstrates that data exports contain more detailed security events than standard account interfaces.
            </p>
          </v-card>
        </v-col>
      </v-row>

      <!-- Footer -->
      <v-divider class="my-8"></v-divider>
      <footer class="py-4 text-center">
        <p class="text-caption secondary--text mb-0">
          &copy; 2026 TOOLNAME &nbsp;|&nbsp;
          <v-btn text x-small href="#">Privacy</v-btn>
          <v-btn text x-small href="#">Terms</v-btn>
        </p>
      </footer>
    </v-container>
  </v-app>
</template>

<script>
import PageHeader from '../components/Navigation/PageHeader.vue'

export default {
  name: 'Home',
  components: {
    PageHeader,
  },
  data() {
    return {
      drawer: false,
      features: [
        'Timeline view of login events and security changes',
        'Device and network identification across platforms',
        'Comparison of platform activity logs with standard account interfaces',
        'Annotation tools for marking suspicious activities',
        'Local-first processing - no data leaves your browser',
        'Support for Google, Discord, Apple, Facebook, Instagram, and Snapchat',
      ],
      supportedPlatforms: [
        { name: 'Google', icon: 'mdi-google' },
        { name: 'Discord', icon: 'mdi-discord' },
        { name: 'Apple', icon: 'mdi-apple' },
        { name: 'Facebook', icon: 'mdi-facebook' },
        { name: 'Instagram', icon: 'mdi-instagram' },
        { name: 'Snapchat', icon: 'mdi-snapchat' },
      ],
    }
  },
  methods: {
    goToSketch() {
      this.$router.push({ name: 'Explore' })
    },
  },
}
</script>

<style scoped lang="scss">

.h-100 {
  height: 100%;
}

.video-placeholder {
  background: linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%);
}

.step-number {
  font-size: 2rem;
}

.fill-height {
  height: 100%;
}

.github-logo {
  height: 22px;
  width: 22px;
  vertical-align: middle;
}

@media (max-width: 960px) {
  .pl-md-8 {
    padding-left: 0 !important;
    margin-top: 2rem;
  }
}

</style>
