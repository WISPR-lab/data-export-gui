<!--
Delete Data Button & Dialog (Merged Component)
-->
<template>
  <div>
    <!-- Button Trigger -->
    <v-btn
      v-if="btnType === 'leftPanel'"
      small
      text
      color="error"
      class="delete-btn"
      style="width: 100%; height:2rem"
      @click="isOpen = true"
    >
      <v-icon left small>mdi-trash-can-outline</v-icon>
      Delete All Data
    </v-btn>
    <v-btn
      v-else
      rounded
      depressed
      class="delete-btn"
      @click="isOpen = true"
    >
      <v-icon left>mdi-trash-can-outline</v-icon>
      Delete All Data
    </v-btn>

    <!-- Dialog Confirmation -->
    <v-dialog v-model="isOpen" width="500px">
      <v-card>
        <v-card-title class="headline">Delete all data?</v-card-title>
        <v-card-text>
          <p>This will permanently delete all imported data from this project.</p>
          <p style="color: #000; font-weight: bold;">This action cannot be undone.</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="isOpen = false">Cancel</v-btn>
          <v-btn 
            text 
            @click="handleDelete" 
            :loading="isDeleting"
            style="color: #d32f2f !important; font-weight: bold;"
          >
            Delete All Data
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { clearAllTables } from '@/database/index.js';
import { OPFSManager } from '@/storage/opfs_manager.js';

export default {
  name: 'DeleteDataButton',
  props: {
    btnType: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      isOpen: false,
      isDeleting: false
    };
  },
  methods: {
    async handleDelete() {
      try {
        this.isDeleting = true;
        await clearAllTables();

        const opfsManager = new OPFSManager();
        await opfsManager.clearTempStorage();

        localStorage.clear();
        this.$store.commit('RESET_STATE');
        
        this.isOpen = false;
        
        this.$store.dispatch('setSnackBar', {
          message: 'All data has been permanently deleted.',
          color: 'success',
          timeout: 5000
        });
        
        setTimeout(() => {
          location.reload();
        }, 1000);
        
        this.$emit('deleted');
      } catch (error) {
        console.error('Error deleting all data:', error);
        this.$store.dispatch('setSnackBar', {
          message: 'Error deleting data: ' + error.message,
          color: 'error',
          timeout: 5000
        });
        this.isDeleting = false;
      }
    }
  }
}
</script>

<style scoped>
.delete-btn {
  background-color: rgba(211, 47, 47, 0.08) !important;
  border-radius: 2px !important;
}
</style>
