<template>
  <v-app-bar :app="app" :clipped-left="clippedLeft" flat color="white" class="border-bottom">
    <div class="header-content">
      <!-- Left side: Drawer Toggle (optional) + Logo + Project Name -->
      <div class="header-left">
        <v-btn v-if="showDrawer" icon @click="$emit('toggle-drawer')" class="mr-2">
          <v-icon title="Toggle left panel">mdi-menu</v-icon>
        </v-btn>
        
        <router-link to="/" class="d-flex align-center" style="text-decoration: none; color: inherit;">
          <img :src="LestradeLogo" alt="LEStrADE Logo" height="32" class="mr-2" />
        </router-link>


        <!-- Project Name Section -->
        <div v-if="isProjectInfoVisible" class="ml-4 d-none d-sm-flex align-center">
          <div v-if="demoMode" class="blue white--text px-3 py-1 rounded font-weight-bold" style="font-size: 0.85em; letter-spacing: 0.5px;">
            INTERACTIVE DEMO
          </div>
          <v-hover v-else-if="project && project.name" v-slot="{ hover }">
            <div class="d-flex align-center">
              <div
                @dblclick="$emit('rename-project')"
                style="font-size: 1.1em; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 300px;"
                :title="project.name"
              >
                <span class="font-weight-bold">Project:</span>&nbsp; {{ project.name }}
              </div>
              <v-icon title="Rename Project" small class="ml-3" v-if="hover" @click="$emit('rename-project')">mdi-pencil</v-icon>
            </div>
          </v-hover>
        </div>
      </div>

      <!-- Desktop Navigation (shown on md and up) -->
      <div class="header-nav d-none d-md-flex">
        <v-btn text router-link to="/" class="nav-link">Home</v-btn>
        <v-btn text router-link to="/events" class="nav-link">Explore My Data</v-btn>
        
        <!-- Tutorials Dropdown (Help Docs) -->
        <v-menu offset-y open-on-hover>
          <template v-slot:activator="{ on, attrs }">
            <v-btn text v-bind="attrs" v-on="on" class="nav-link" id="tsTutorialsButton">
              Tutorials
              <v-icon small right>mdi-chevron-down</v-icon>
            </v-btn>
          </template>
          <v-list>
            <v-list-item to="/how-to-request">
              <v-list-item-icon>
                <v-icon>mdi-help-circle-outline</v-icon>
              </v-list-item-icon>
              <v-list-item-title>How to Request Your Data</v-list-item-title>
            </v-list-item>
            <v-list-item to="/demo/events" class="interactive-demo-link">
              <v-list-item-icon>
                <v-icon>mdi-play-circle</v-icon>
              </v-list-item-icon>
              <v-list-item-title>Interactive Demo</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>

        <v-btn text href="#" class="nav-link">Research</v-btn> <!-- todo --> 
        <v-btn text href="https://github.com/WISPR-lab/data-export-gui/" target="_blank" class="nav-link">
          GitHub
          <v-icon small class="ml-1">mdi-github</v-icon>
        </v-btn>
      </div>

      <!-- Mobile Menu (shown only on sm and down) -->
      <PageHeaderMobileMenu visibilityClass="d-md-none" />
    </div>
  </v-app-bar>
</template>

<script>
import PageHeaderMobileMenu from './PageHeaderMobileMenu.vue'
import LestradeLogo from '@/assets/images/lestrade_logo.svg'

export default {
  name: 'PageHeader',
  components: {
    PageHeaderMobileMenu,
  },
  props: {
    app: {
      type: Boolean,
      default: false,
    },
    clippedLeft: {
      type: Boolean,
      default: false,
    },
    showDrawer: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    project() {
      return this.$store.state.project
    },
    demoMode() {
      return this.$store.state.demoMode
    },
    isProjectInfoVisible() {
      const allowedRoutes = ['Explore', 'Devices', 'DemoExplore', 'DemoDevices']
      return allowedRoutes.includes(this.$route.name)
    },
  },
  methods: {
    exitDemo() {
      const DemoController = require('@/demo/DemoController.js').default
      DemoController.complete()
      this.$router.push('/')
    },
  },
  data() {
    return {
      LestradeLogo,
    }
  },
}
</script>

<style scoped lang="scss">
.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-nav {
  display: flex;
  align-items: center;
}

.tool-name {
  font-weight: 500;
  font-size: 16px;
}

.nav-link {
  margin: 0 4px;
}

.border-bottom {
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
}

::v-deep .theme--dark .border-bottom {
  border-bottom: 1px solid hsla(0, 0%, 100%, 0.12) !important;
}
</style>
