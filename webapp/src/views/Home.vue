<template>
  <v-app>
    <PageHeader />

    <div class="main-container">
      <div class="text-center mb-12 hero-spacing">
        <h1 class="text-h4 font-weight-bold secondary--text mb-4">
          Visualize your account security status in one timeline.
        </h1>
        <p class="text-h5 secondary--text mb-8 font-weight-regular">
          Online platforms let you download data exports containing your personal data. <br/>
          <strong>LEStraDE</strong> shows you what's actually in it, privately in your browser.
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

      <div class="mb-20">
        <v-card class="card-shadow pa-8 mb-4">
          <h3 class="text-h5 font-weight-medium secondary--text mb-4 text-center">What LEStraDE Does</h3>
          <p class="text-body1 secondary--text text-center">
            When you're trying to understand if an account has been compromised, standard security settings often don't provide enough information. 
            <span class="font-weight-bold">LEStraDE</span> lets you access and analyze the security data these platforms already collect about you.
          </p>
        </v-card>

        <div class="arrow-container mb-4">
          <v-icon color="secondary" size="32">mdi-arrow-down</v-icon>
        </div>

        <v-card class="card-shadow pa-8 mb-4">
          <h3 class="text-h5 font-weight-medium secondary--text mb-4 text-center">Import Your Data</h3>
          <p class="text-body1 secondary--text mb-4 text-center">
            Request a data export from any supported platform—a file containing your account's complete security history. LEStraDE processes it <strong>locally</strong> in your browser, never uploading or storing your data elsewhere.
          </p>
          <div class="d-flex justify-center">
            <v-btn
              large
              outlined
              color="primary"
              to="/how-to-request"
            >
              <v-icon left>mdi-information-outline</v-icon>
              How to request your data
            </v-btn>
          </div>
        </v-card>

        <div class="arrow-container mb-4">
          <v-icon color="secondary" size="32">mdi-arrow-down</v-icon>
        </div>

        <v-card class="card-shadow pa-8 mb-4">
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
        </v-card>
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
import heroScreenshot from '@/assets/hero_screenshot.png'

export default {
  name: 'Home',
  components: {
    PageHeader,
    DiscordIcon,
  },
  data() {
    return {
      heroScreenshot,
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
