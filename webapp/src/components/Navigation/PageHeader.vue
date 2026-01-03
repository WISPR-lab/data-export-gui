<template>
  <v-app-bar flat color="white" class="border-bottom">
    <div class="header-content">
      <!-- Left side: Logo + Tool Name -->
      <div class="header-left">
        <v-icon size="24">mdi-database-search</v-icon>
        <span class="tool-name ml-2">takeout-tool</span>
      </div>

      <!-- Desktop Navigation (shown on md and up) -->
      <div class="header-nav d-none d-md-flex">
        <v-btn text router-link to="/" class="nav-link">Home</v-btn>
        <v-btn text href="/sketch/1/explore" class="nav-link">Explore My Data</v-btn>
        <v-btn text router-link to="/how-to-request" class="nav-link">Tutorials</v-btn>
        <v-btn text href="#" class="nav-link">Research</v-btn>
        <v-btn text href="https://github.com/google/timesketch" target="_blank" class="nav-link">
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

export default {
  name: 'PageHeader',
  components: {
    PageHeaderMobileMenu,
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
