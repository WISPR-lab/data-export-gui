<!--
UploadErrorDisplay.vue

Extracted error/warning display logic. Handles:
- Error type classification (user vs system errors)
- Smart messaging based on error type
- Additional error details collapsible
- Warnings section
- Fallback error display

Props:
  - errorType: error category (from ERROR_TYPES)
  - errors: array of error messages
  - warnings: array of warning messages
-->
<template>
  <div>
    <!-- Primary Error Alert -->
    <div v-if="errorType" class="mb-6">
      <v-alert outlined :type="isUserError ? 'warning' : 'error'" class="mb-2">
        <strong>{{ isUserError ? 'Please fix your data:' : 'System Error:' }}</strong>
        <br />
        {{ errorDisplayMessage }}
      </v-alert>
      
      <!-- Additional Errors Collapsible -->
      <div v-if="errors.length > 1" class="mt-2">
        <details class="text-body2">
          <summary>Additional details</summary>
          <div class="mt-2">
            <div v-for="(err, idx) in errors.slice(1)" :key="idx" class="text-body2 mb-1">
              • {{ err }}
            </div>
          </div>
        </details>
      </div>
    </div>

    <!-- Warnings Display -->
    <div v-if="warnings.length > 0" class="mb-6">
      <v-alert v-for="(warning, index) in warnings" :key="index" outlined type="info" class="mb-2">
        {{ warning }}
      </v-alert>
    </div>

    <!-- Fallback Error Display (for local component validation errors) -->
    <div v-if="localErrors.length > 0 && !errorType" class="mb-6">
      <v-alert v-for="(error, index) in localErrors" :key="index" outlined type="error" class="mb-2">
        {{ error }}
      </v-alert>
    </div>
  </div>
</template>

<script>
import { getErrorMessage, isUserError } from '../../errorTypes.js';

export default {
  name: 'UploadErrorDisplay',
  props: {
    errorType: {
      type: String,
      default: null,
    },
    errors: {
      type: Array,
      default: () => [],
    },
    warnings: {
      type: Array,
      default: () => [],
    },
    localErrors: {
      type: Array,
      default: () => [],
    },
  },
  computed: {
    isUserError() {
      return this.errorType ? isUserError(this.errorType) : false;
    },
    errorDisplayMessage() {
      if (!this.errorType) {
        return (this.errors && this.errors[0]) || 'An error occurred';
      }

      const baseMessage = getErrorMessage(this.errorType);
      
      if (this.isUserError) {
        return baseMessage;
      } else {
        return `${baseMessage} (Please try again or contact support)`;
      }
    },
  },
};
</script>

<style scoped lang="scss">
// Styling for collapsible details
details {
  cursor: pointer;
  
  summary {
    font-weight: 500;
    text-decoration: underline;
    
    &:hover {
      opacity: 0.8;
    }
  }
}
</style>
