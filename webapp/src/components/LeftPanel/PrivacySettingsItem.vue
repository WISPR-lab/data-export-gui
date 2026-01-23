<template>
  <div>
    <div
      v-if="iconOnly"
      class="pa-4"
      style="cursor: pointer"
      @click="$emit('toggleDrawer'); $emit('openSettings')"
      title="Privacy & Visibility Settings"
    >
      <v-icon>mdi-shield-account</v-icon>
    </div>

    <div v-else>
      <div
        class="pa-4"
        style="cursor: pointer"
        @click="$emit('openSettings')"
        :class="$vuetify.theme.dark ? 'dark-hover' : 'light-hover'"
      >
        <v-icon left>mdi-shield-account</v-icon>
        <span>Privacy & Visibility Settings</span>
      </div>
      <v-divider></v-divider>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PrivacySettingsItem',
  props: {
    iconOnly: {
      type: Boolean,
      default: false
    }
  }
};
</script>
