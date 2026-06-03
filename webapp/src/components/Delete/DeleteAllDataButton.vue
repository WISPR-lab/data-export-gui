<!--
Delete All Data Button
Triggers the delete data confirmation dialog
-->
<template>
  <DeleteAllDataDialog>
    <template v-slot="slotProps">
      <v-btn
        v-if="btnType === 'leftPanel'"
        small
        text
        color="error"
        class="delete-btn"
        style="width: 100%; height:2rem"
        v-bind="{ ...slotProps.attrs, ...$attrs }"
        v-on="{ ...slotProps.on, ...$listeners }"
      >
        <v-icon left small>mdi-trash-can-outline</v-icon>
        Delete All Data
      </v-btn>
      <v-btn
        v-else
        rounded
        depressed
        class="delete-btn"
        v-bind="{ ...slotProps.attrs, ...$attrs }"
        v-on="{ ...slotProps.on, ...$listeners }"
      >
        <v-icon left>mdi-trash-can-outline</v-icon>
        Delete All Data
      </v-btn>
    </template>
  </DeleteAllDataDialog>
</template>

<script>
import DeleteAllDataDialog from './DeleteAllDataDialog.vue'

export default {
  name: 'DeleteAllDataButton',
  inheritAttrs: false,
  props: {
    btnType: {
      type: String,
      default: ''
    }
  },
  components: {
    DeleteAllDataDialog,
  },
}
</script>

<style scoped>
.delete-btn {
  background-color: rgba(211, 47, 47, 0.08) !important;
  border-radius: 2px !important;
}
</style>
