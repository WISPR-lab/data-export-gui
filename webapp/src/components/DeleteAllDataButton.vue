<!--
Delete All Data Button
Triggers the delete data confirmation dialog
-->
<template>
  <v-btn 
    rounded 
    depressed 
    color="#d32f2f" 
    @click="handleClick"
    style="color: white !important; margin-right: 24px;"
  >
    <v-icon left>mdi-trash-can-outline</v-icon>
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
