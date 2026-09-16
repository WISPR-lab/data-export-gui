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
      <v-list-item router-link to="/events" :active="$route.path.includes('sketch')">
        <v-list-item-title>Explore My Data</v-list-item-title>
      </v-list-item>
      <v-list-item router-link to="/how-to-request" :active="$route.path === '/how-to-request'">
        <v-list-item-title>How to Request Your Data</v-list-item-title>
      </v-list-item>
      <v-list-item router-link to="/demo/events">
        <v-list-item-title>Interactive Demo</v-list-item-title>
      </v-list-item>
      <v-list-item disabled>
        <v-list-item-title>Research <span class="grey--text text--darken-1">(Coming soon)</span></v-list-item-title>
      </v-list-item>
      <v-list-item disabled>
        <v-list-item-title>
          <v-icon medium class="mr-2 mb-1">mdi-github</v-icon>
          <span class="grey--text text--darken-1">(Coming soon)</span>
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
