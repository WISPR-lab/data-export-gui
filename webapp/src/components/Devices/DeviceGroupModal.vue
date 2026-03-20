<template>
  <v-dialog v-model="internalValue" max-width="500px">
    <v-card v-if="source && target">
      <v-toolbar flat dense color="grey lighten-4" height="64">
        <v-toolbar-title class="text-h6 font-weight-bold ml-2">Is this the same device?</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon @click="cancel">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text class="pa-6">
        <div class="body-1 mb-4">
          Are you sure you want to combine the activity from <strong>{{ source.label }}</strong> into the <strong>{{ target.user_label || target.model }}</strong> profile?
        </div>
        
        <v-sheet rounded="lg" color="blue lighten-5" class="pa-4 mb-4 d-flex align-center border-blue">
          <v-icon color="blue" class="mr-4">mdi-map-marker-distance</v-icon>
          <div>
            <div class="body-2 blue--text text--darken-2">TODO WHY THEY MATCH.</div>
          </div>
        </v-sheet>

        <div class="body-2 grey--text text--darken-1 italic">
          <v-icon small class="mr-1">mdi-information-outline</v-icon>
          You can undo this later.
        </div>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions class="pa-4">
        <v-spacer></v-spacer>
        <v-btn text @click="cancel" class="text-none">
          Cancel
        </v-btn>
        <v-btn color="primary" @click="confirm" class="text-none px-6">
          Merge device data
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: 'DeviceGroupModal',
  props: {
    value: {
      type: Boolean,
      default: false
    },
    source: {
      type: Object,
      default: () => null
    },
    target: {
      type: Object,
      default: () => null
    }
  },
  computed: {
    internalValue: {
      get() { return this.value; },
      set(val) { this.$emit('input', val); }
    }
  },
  methods: {
    confirm() {
      this.$emit('confirm');
    },
    cancel() {
      this.$emit('input', false);
    }
  }
}
</script>
