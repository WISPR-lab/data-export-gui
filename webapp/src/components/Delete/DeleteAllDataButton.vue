<!--
Delete All Data Button
Triggers the delete data confirmation dialog
-->
<template>
  <v-btn 
    small
    text
    color="error"
    @click="handleClick"
    class="delete-btn"
  >
    <v-icon left small>mdi-trash-can-outline</v-icon>
    Delete All Data
  </v-btn>
</template>

<script>
export default {
  name: 'DeleteAllDataButton',
  methods: {
    handleClick() {
      this.$emit('click')
    },
  },
}
</script>

<style scoped>
.delete-btn {
  background-color: rgba(211, 47, 47, 0.08) !important;
  border-radius: 2px !important;
}
</style>
