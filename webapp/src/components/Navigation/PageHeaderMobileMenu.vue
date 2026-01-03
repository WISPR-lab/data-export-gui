<template>
  <v-menu offset-y>
    <template v-slot:activator="{ on, attrs }">
      <v-btn
        icon
        :class="visibilityClass"
        v-bind="attrs"
        v-on="on"
      >
        <v-icon>mdi-dots-vertical</v-icon>
      </v-btn>
    </template>
    <v-list>
      <v-list-item router-link to="/" :active="$route.path === '/'">
        <v-list-item-title>Home</v-list-item-title>
      </v-list-item>
      <v-list-item router-link to="/sketch/1/explore" :active="$route.path.includes('sketch')">
        <v-list-item-title>Explore My Data</v-list-item-title>
      </v-list-item>
      <v-list-item router-link to="/how-to-request" :active="$route.path === '/how-to-request'">
        <v-list-item-title>Tutorials</v-list-item-title>
      </v-list-item>
      <v-list-item href="#">
        <v-list-item-title>Research</v-list-item-title>
      </v-list-item>
      <v-list-item href="https://github.com/google/timesketch" target="_blank">
        <v-list-item-title>GitHub<v-icon medium class="ml-2 mb-1">mdi-github</v-icon>
        </v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>


<script>
export default {
  name: 'PageHeaderMobileMenu',
  props: {
    visibilityClass: {
      type: String,
      default: 'd-md-none',  // Default: hide on md+ (responsive)
    },
  },
}
</script>
