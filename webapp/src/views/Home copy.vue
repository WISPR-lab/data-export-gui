<template>
  <v-app>

   <!-- primary: #1976D2 (blue)
        secondary: #424242 (grey)
        accent: #82B1FF (light blue)
        error: #FF5252 (red)
        info: #2196F3 (blue)
        success: #4CAF50 (green)
        warning: #FFC107 (amber) -->


    <!-- Header -->
    <v-container max-width="1200px" class="py-12 align-center justify-center">
      <v-row class="d-flex align-center justify-space-between mb-12">
        <v-col cols="12" sm="7" class="d-flex align-center">
          <h1 class="text-h2 font-weight-bold primary--text mb-0">
            Tool Name
          </h1>
        </v-col>

        <v-col cols="12" sm="5" class="d-flex align-center justify-end">
          <v-btn large rounded color="#d3d3d3" href="https://github.com/" class="px-6">
            <svg aria-hidden="true" height="24" viewBox="0 0 24 24" version="1.1" width="24" data-view-component="true" class="octicon octicon-mark-github">
                <path fill="secondary" d="M12 1C5.923 1 1 5.923 1 12c0 4.867 3.149 8.979 7.521 10.436.55.096.756-.233.756-.522 0-.262-.013-1.128-.013-2.049-2.764.509-3.479-.674-3.699-1.292-.124-.317-.66-1.293-1.127-1.554-.385-.207-.936-.715-.014-.729.866-.014 1.485.797 1.691 1.128.99 1.663 2.571 1.196 3.204.907.096-.715.385-1.196.701-1.471-2.448-.275-5.005-1.224-5.005-5.432 0-1.196.426-2.186 1.128-2.956-.111-.275-.496-1.402.11-2.915 0 0 .921-.288 3.024 1.128a10.193 10.193 0 0 1 2.75-.371c.936 0 1.871.123 2.75.371 2.104-1.43 3.025-1.128 3.025-1.128.605 1.513.221 2.64.111 2.915.701.77 1.127 1.747 1.127 2.956 0 4.222-2.571 5.157-5.019 5.432.399.344.743 1.004.743 2.035 0 1.471-.014 2.654-.014 3.025 0 .289.206.632.756.522C19.851 20.979 23 16.854 23 12c0-6.077-4.922-11-11-11Z"></path>
            </svg>&nbsp;&nbsp;View on GitHub
          </v-btn>
        </v-col>
      </v-row>


      <v-row class="align-center mb-12">
        <v-col cols="12">
          <v-container class="text-center" style="max-width:800px; margin:0 auto;">

            <p class="text-h4 secondary--text mb-6 line-height-relaxed">
              <!-- [TOOL NAME] is an open-source tool that helps end-users <span class="primary--text font-weight-black">review and annotate account security incidents</span>
              using data exports from major platforms like Google and Meta. -->
              Review and annotate <span class="primary--text font-weight-black">account security incidents</span> using data exports from your online accounts.
            </p>

            <v-card class="pa-8 light-highlight rounded mb-10" style="min-height: 200px; background: linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%);">
              <div class="d-flex align-center justify-center fill-height">
                <div class="text-center">
                  <v-icon size="64" class="mb-4 secondary--text">mdi-image-outline</v-icon>
                  <p class="text-body2 secondary--text">Featured image coming soon</p>
                </div>
              </div>
            </v-card>

            <p class="text-body2 secondary--text pt-8 mb-8 line-height-relaxed">
              [TOOL NAME] is an open-source tool that  
              Designed for technology consultants supporting survivors of technology-facilitated abuse, this tool makes it 
              easier to uncover login attempts, device activity, and security events that might indicate an account has been 
              compromised by someone with intimate knowledge of the target.
            </p>

            <div class="d-flex flex-wrap gap-3 mb-8 justify-center">
              <PlatformSelector>
                <template v-slot="{ attrs, on }">
                  <v-btn large rounded color="primary" v-bind="attrs" v-on="on" class="px-6">
                    <v-icon left>mdi-cloud-upload</v-icon>
                    Import Data Export
                  </v-btn>
                </template>
              </PlatformSelector>
              <v-btn large outlined rounded color="primary" to="/how-to-request" class="px-6" >
                <v-icon left>mdi-help-circle-outline</v-icon>
                How to Request Data
              </v-btn>
          </div>


            
          </v-container>
        </v-col>
      </v-row>

      <!-- Main Content Row -->
      <v-row class="align-center mb-12">
        <v-col cols="12" md="7">
          

          <p class="text-body1 secondary--text mb-8 line-height-relaxed">
            Designed for technology consultants supporting survivors of technology-facilitated abuse, this tool makes it 
            easier to uncover login attempts, device activity, and security events that might indicate an account has been 
            compromised by someone with intimate knowledge of the target.
          </p>

          <!-- Key Features -->
          <div class="mb-8">
            <h3 class="text-h6 font-weight-medium mb-4">Key Capabilities</h3>
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
          </div>


          <!-- Research Context -->
          <div class="pa-4 light-highlight rounded">
            <p class="text-caption font-weight-medium secondary--text mb-2">ABOUT THIS TOOL</p>
            <p class="text-body2 secondary--text mb-0">
              This tool operationalizes findings from the research paper 
              <router-link to="#" class="primary--text font-weight-medium">
                "Hidden in Plain Bytes: Investigating Interpersonal Account Compromise with Data Exports"
              </router-link>
              which demonstrates that data exports contain more detailed security events and login histories than 
              standard account security interfaces.
            </p>
          </div>
        </v-col>

        <!-- Right Column: Video/Visual Placeholder -->
        <v-col cols="12" md="5" class="pl-md-8">
          <!-- TODO: Replace with embedded tutorial video -->
          <!-- <div class="video-placeholder rounded elevation-2">
            <v-card class="fill-height d-flex align-center justify-center" style="min-height: 400px;">
              <div class="text-center pa-8">
                <v-icon size="64" class="mb-4 secondary--text">mdi-play-circle-outline</v-icon>
                <h3 class="text-h6 font-weight-medium mb-2">Tutorial Video</h3>
                <p class="text-body2 secondary--text">
                  Quick walkthrough of how to use this tool in a consultation setting
                </p>
                <v-btn
                  text
                  color="primary"
                  class="mt-4"
                  disabled
                >
                  Video coming soon
                </v-btn>
              </div>
            </v-card>
          </div> -->

          <!-- Quick Stats -->
          <v-card class="mt-6 pa-6 light-highlight">
            <h4 class="text-body2 font-weight-medium mb-4">Supported Platforms</h4>
            <div class="d-flex flex-wrap gap-2">
              <v-chip
                v-for="platform in supportedPlatforms"
                :key="platform"
                small
                outlined
              >
                {{ platform }}
              </v-chip>
            </div>
          </v-card>
        </v-col>
      </v-row>

      <!-- How It Works Section -->
      <v-divider class="my-12"></v-divider>

      <div class="mb-12">
        <h2 class="text-h4 font-weight-light mb-8 text-center">How It Works</h2>
        
        <v-row>
          <v-col cols="12" md="3" v-for="step in workflowSteps" :key="step.number">
            <v-card class="h-100 pa-6 text-center" outlined>
              <div class="step-number primary--text text-h4 font-weight-medium mb-4">
                {{ step.number }}
              </div>
              <h3 class="text-body1 font-weight-medium mb-3">{{ step.title }}</h3>
              <p class="text-body2 secondary--text line-height-relaxed">{{ step.description }}</p>
            </v-card>
          </v-col>
        </v-row>
      </div>

      <!-- Important Notes -->
      <v-alert outlined type="warning" class="mb-0">
        <strong>Privacy & Security:</strong> All data processing happens locally in your browser. 
        No data is sent to external servers. Follow safe handling practices provided in your consultation appointments.
      </v-alert>
    </v-container>
  </v-app>
</template>

<script>
import BrowserDB from '../database.js'
import PlatformSelector from '../components/PlatformSelector.vue'

export default {
  name: 'Home',
  components: {
    PlatformSelector,
  },
  data() {
    return {
      loading: false,
      features: [
        'Timeline view of login events and security changes',
        'Device and network identification across platforms',
        'Comparison of platform activity logs with standard account interfaces',
        'Annotation tools for marking suspicious activities',
        'Local-first processing - no data leaves your browser',
        'Support for Google, Discord, Apple, Facebook, Instagram, and Snapchat',
      ],
      supportedPlatforms: ['Google', 'Discord', 'Apple', 'Facebook', 'Instagram', 'Snapchat'],
      workflowSteps: [
        {
          number: 1,
          title: 'Request Data Export',
          description: 'Use our guides to request data exports from the platform(s) you want to investigate.',
        },
        {
          number: 2,
          title: 'Download Safely',
          description: 'Download the ZIP file to a secure, password-protected device or USB drive.',
        },
        {
          number: 3,
          title: 'Import and Analyze',
          description: 'Upload the data export here to visualize timelines and security events.',
        },
        {
          number: 4,
          title: 'Review and Annotate',
          description: 'Work with your consultant to review events and annotate suspicious activity.',
        },
      ],
    }
  },
  mounted() {
    // Initialize default sketch if it doesn't exist
    this.ensureDefaultSketch()
  },
  methods: {
    async ensureDefaultSketch() {
      try {
        // Check if default sketch (ID 1) exists
        const response = await BrowserDB.getSketch(1)
        if (response.data.objects[0]) {
          // Default sketch exists, we can proceed
          return
        }
      } catch (e) {
        // Sketch doesn't exist, create it
      }

      // Create default sketch
      try {
        await BrowserDB.createSketch({
          name: 'My Timeline',
          description: 'Personal forensic timeline',
          user_id: 'local-user',
          label_string: 'default',
          status: 'active',
        })
      } catch (e) {
        console.error('Error creating default sketch:', e)
      }
    },
    goToExplore() {
      this.loading = true
      // Navigate to explore view with default sketch (ID 1)
      this.$router.push({ name: 'Explore', params: { sketchId: 1 } })
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
