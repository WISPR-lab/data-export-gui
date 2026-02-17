<!--
Delete All Data Confirmation Dialog
-->
<template>
  <v-dialog v-model="isOpen" width="500px" @input="handleDialogChange">
    <v-card>
      <v-card-title class="headline">Delete all data?</v-card-title>
      <v-card-text>
        <p>This will permanently delete all imported data from this project.</p>
        <p style="color: #000; font-weight: bold;">This action cannot be undone.</p>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn text @click="handleCancel">Cancel</v-btn>
        <v-btn text @click="handleDelete" style="color: #d32f2f !important; font-weight: bold;">Delete All Data</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { wipeAllData } from '@/storage/nuke';  


export default {
  name: 'DeleteAllDataDialog',
  props: {
    open: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      isOpen: this.open,
      isDeleting: false,
    }
  },
  watch: {
    open(newVal) {
      this.isOpen = newVal
    },
  },
  methods: {
    handleCancel() {
      this.isOpen = false
      this.$emit('close')
    },
    async handleDelete() {
      try {
        this.isDeleting = true
        await wipeAllData()
        
        // Reset Vuex store to clear stale sketch/timeline data
        this.$store.commit('RESET_STATE')
        
        this.isOpen = false
        
        // Show success message
        this.$store.dispatch('setSnackBar', {
          message: 'All data has been permanently deleted.',
          color: 'success',
          timeout: 5000,
        })
        
        // Force page reload after delay
        setTimeout(() => {
          location.reload()
        }, 1000)
        
        this.$emit('deleted')
      } catch (error) {
        console.error('Error deleting all data:', error)
        this.$store.dispatch('setSnackBar', {
          message: 'Error deleting data: ' + error.message,
          color: 'error',
          timeout: 5000,
        })
        this.isDeleting = false
      }
    },
    handleDialogChange(value) {
      this.isOpen = value
      if (!value) {
        this.$emit('close')
      }
    },
  },
}
</script>
