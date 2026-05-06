<template>
  <v-app>
    <PageHeader />

    <div class="main-container">
      <div class="text-center mb-12 hero-spacing">
        <img :src="LestradeLogo" alt="LEStrADE Logo" height="80" class="mr-2" />
        <h1 class="text-h4 secondary--text mb-4">
          <!-- <span class="font-weight-black">L</span>ocal <span class="font-weight-black">E</span>ngine for <span class="font-weight-black">Str</span>uctured <span class="font-weight-black">A</span>nalysis of <span class="font-weight-black">D</span>ata <span class="font-weight-black">E</span>xports -->
          <!-- Visualize your account security status in one timeline. -->
        </h1>
        <p class="text-h5 secondary--text mb-8 font-weight-regular">
          <strong>L</strong>ocal <strong>E</strong>ngine for <strong>Str</strong>uctured <strong>A</strong>nalysis of <strong>D</strong>ata <strong>E</strong>xports
          (LEStrADE<sup>*</sup>) is an open-source visualization tool that helps users understand their account security history using <strong>data exports</strong> from online platforms.
          <!-- Online platforms let you download data expor, usually containing your personal data. <br/>
          <strong>LEStrADE</strong> can show you what's in it, privately in your browser. -->
        </p>
        <p class="text-body1 secondary--text mb-8 font-weight-regular">
          * Named after the minor Sherlock Holmes character, <a href="https://en.wikipedia.org/wiki/Inspector_Lestrade" target="_blank">Inspector Lestrade</a>
        </p>
        <div class="d-flex justify-center gap-3">
          <v-btn
            large
            outlined
            color="primary"
            to="/how-to-request"
          >
            <v-icon left>mdi-information-outline</v-icon>
            Get your data export
          </v-btn>
          <v-btn
            large
            color="primary"
            @click="goToSketch"
          >
            <v-icon left>mdi-play</v-icon>
            Explore your data
          </v-btn>
      
        </div>
      </div>


      <div class="mb-20">
        <img :src="heroScreenshot" alt="Dashboard screenshot" class="screenshot card-shadow" />
      </div>
      <v-alert type="primary" dense class="font-weight-medium mt-10 mb-10 text-center"><span>
        LEStrADE is an academic tool in early beta. We welcome feedback to help us improve the tool on GitHub!
      </span></v-alert>

      <div class="mb-20">
        <v-card class="card-shadow pa-10 pl-16 pr-16 mb-4">
          <h3 class="text-h5 font-weight-medium secondary--text mb-8 text-center">What are <i>data exports</i>?</h3>
          <v-row >
            <v-col cols="12" sm="7" class="d-flex flex-column justify-center align-center">
              <p class="text-body1 secondary--text mb-4 text-left">
                Due to <a href="https://gdpr.eu/what-is-gdpr/" target="_blank">privacy laws</a> in the EU and many US states, users can request their personal data from online platforms.
              </p><p class="text-body1 secondary--text mb-4 text-left">
                This <strong>data export</strong>, usually a ZIP file, often includes a detailed history of security-related events like logins, password changes, and connected devices.
              </p>
            </v-col>
            <v-col cols="12" sm="5" class="d-flex flex-column justify-center align-end">
              <!-- todo add image --> 
               <img :src="GoogleTakeout" alt="Google Takeout screenshot" style="max-width: 70%;"/>

            </v-col>
          </v-row>
          <div class="d-flex justify-center mt-5">
            <v-btn large outlined color="primary" to="/how-to-request">
              <v-icon left>mdi-information-outline</v-icon>
              How to request your data export
            </v-btn>
          </div>
        </v-card>

        <div class="arrow-container mb-4">
          <v-icon color="secondary" size="32">mdi-arrow-down</v-icon>
        </div>

        <v-card class="card-shadow pa-10 pl-16 pr-16 mb-4">
          <h3 class="text-h5 font-weight-medium secondary--text mb-4 text-center">Features</h3>
          <p class="text-body1 secondary--text mb-4 text-left">
            LEStrADE is designed do "consensual digital forensics" with data exports for the purpose of helping users identify suspicious activity by <strong>someone malicious accessing their account</strong>, i.e., logging in or changing passwords. 
            <br/>Features include:
            <!-- It is not meant to be a comprehensive, proactive security tool, but rather a way to make the security data in these exports more accessible and understandable for users. -->
          </p>
          <v-row>
            <v-col cols="12" sm="6" class="d-flex flex-column justify-center align-start">
              <ul class="text-body1 secondary--text mb-0"> <!-- style="list-style-type: disc; padding-left: 1.5rem;">-->
                <li>Extract security-related data from complex files.</li>
                <li>Display events in a searchable timeline.</li>
                <li>Isolate logged-in devices and IP addresses.</li>
                <li>Flag and annotate suspicious events and devices.</li>
                <li>Compare data from multiple platforms.</li>
              </ul>
            </v-col>
            <v-col cols="12" sm="6" class="d-flex flex-column justify-center align-center">
              <v-alert type="success" icon="$info" prominent class="font-weight-medium">
                <span class="text-h6 font-weight-bold">Privacy</span><br/>
                All data processing is done locally in the browser. Your data export file is never uploaded to any server.
              </v-alert>
            </v-col>
          </v-row>

        </v-card>
<!-- 
        <div class="arrow-container mb-4">
          <v-icon color="secondary" size="32">mdi-arrow-down</v-icon>
        </div> -->

        <!-- <v-card class="card-shadow pa-8 mb-4">
          <h3 class="text-h5 font-weight-medium secondary--text mb-6 text-center">Explore &amp; Analyze</h3>
          <v-container style="max-width: 80%; padding: 0; margin: auto;">
            <v-row justify-center no-gutters>
              <v-col v-for="feature in features" :key="feature.text" cols="8" sm="6" class="feature-col">
                <div class="feature-item">
                  <v-icon size="40" color="primary" class="flex-shrink-0">{{ feature.icon }}</v-icon>
                  <p class="text-body1 secondary--text mb-0">{{ feature.text }}</p>
                </div>
              </v-col>
            </v-row>
          </v-container>
        </v-card> -->
      </div>

      <div class="mt-16 mb-20">
        <v-card color="grey lighten-5" class="card-shadow pa-8">
          <h3 class="text-h5 font-weight-medium secondary--text mb-6 text-center">Supported Platforms</h3>
          <v-row>
            <v-col v-for="tierGroup in platformTiers" :key="tierGroup.tier" cols="12" sm="6">
              <p class="text-body2 secondary--text mb-4 text-center font-weight-medium">{{ tierGroup.tier }}</p>
              <div class="d-flex flex-wrap gap-2 justify-center">
                <v-chip
                  v-for="platform in tierGroup.platforms"
                  :key="platform.name"
                  outlined
                >
                  <DiscordIcon v-if="platform.name === 'Discord'" size="14px" margin-right="6px" />
                  <v-icon v-else small left>{{ platform.icon }}</v-icon>
                  {{ platform.name }}
                </v-chip>
              </div>
            </v-col>
          </v-row>
        </v-card>
      </div>

      <v-divider class="my-8"></v-divider>
      <footer class="py-4 text-center">
        <p class="text-caption secondary--text mb-0">
          &copy; 2026 WISPR-lab 
          <!-- &nbsp;|&nbsp; -->
          <!-- <v-btn text x-small href="#">Privacy</v-btn>
          <v-btn text x-small href="#">Terms</v-btn> -->
        </p>
      </footer>
    </div>
  </v-app>
</template>

<script>
import PageHeader from '../components/Navigation/PageHeader.vue'
import DiscordIcon from '../components/DiscordIcon.vue'
import heroScreenshot from '@/assets/images/hero_screenshot.png'
import LestradeLogo from '@/assets/images/lestrade_logo.svg'
import GoogleTakeout from '@/assets/images/google-takeout.png'

export default {
  name: 'Home',
  components: {
    PageHeader,
    DiscordIcon,
  },
  data() {
    return {
      heroScreenshot,
      LestradeLogo,
      GoogleTakeout,
      features: [
        { text: 'Search events and patterns', icon: 'mdi-magnify' },
        { text: 'Flag suspicious activity', icon: 'mdi-flag' },
        { text: 'Add your own notes', icon: 'mdi-pencil' },
        { text: 'Compare data from multiple platforms', icon: 'mdi-compare' },
      ],
      platformTiers: [
        {
          tier: 'Fully Supported',
          platforms: [
            { name: 'Google', icon: 'mdi-google' },
            { name: 'Facebook', icon: 'mdi-facebook' },
          ]
        },
        {
          tier: 'Beta',
          platforms: [
            { name: 'Instagram', icon: 'mdi-instagram' },
            { name: 'Snapchat', icon: 'mdi-snapchat' },
            { name: 'Discord', icon: 'mdi-discord' },
            { name: 'Apple', icon: 'mdi-apple' },
          ]
        },
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
.main-container {
  max-width: 1024px;
  margin: 0 auto;
  padding: 2rem;
}

.card-shadow {
  border-radius: 8px;
  border: 1px solid #e0e0e0 !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.screenshot {
  width: 100%;
  display: block;
}

.hero-spacing {
  margin-top: 40px;
}

@media (min-width: 960px) {
  .hero-spacing {
    margin-top: 80px;
  }
}

.arrow-container {
  display: flex;
  justify-content: center;
  align-items: center;
}

.feature-col {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0;
}

.feature-item {
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: .5rem;
  text-align: center;
  max-width: 300px;
}

.mb-20 {
  margin-bottom: 5rem !important;
}

.mt-16 {
  margin-top: 4rem !important;
}
</style>
