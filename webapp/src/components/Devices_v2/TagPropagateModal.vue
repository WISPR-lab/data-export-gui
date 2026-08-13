<!-- added for WISPR-lab/data-export-gui -->
<template>
  <v-dialog :value="value" max-width="480px" width="auto" @input="$emit('input', $event)">
    <v-card class="pa-5" style="max-width: 480px;">
      <v-card-text class="pa-0 text-body-1 text--primary font-weight-medium">
        {{ message }}
      </v-card-text>

      <v-checkbox
        v-model="dontAskAgain"
        label="Don't ask me again"
        dense
        hide-details
        class="mt-4"
      ></v-checkbox>

      <div class="d-flex justify-end flex-wrap mt-5" style="gap: 8px;">
        <v-btn text small class="text-capitalize" @click="handleChoice(false)">
          {{ deviceOnlyButtonText }}
        </v-btn>
        <v-btn color="primary" depressed small class="text-capitalize" @click="handleChoice(true)">
          {{ allEventsButtonText }}
        </v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: 'TagPropagateModal',
  props: {
    value: { type: Boolean, default: false },
    action: { type: String, default: 'add' }, // 'add' | 'remove'
    tag: { type: String, default: '' },
    eventCount: { type: Number, default: 0 }
  },
  data() {
    return {
      dontAskAgain: false
    };
  },
  computed: {
    isAdd() {
      return this.action === 'add';
    },
    message() {
      var countStr = this.eventCount === 1 ? '1 matching event' : this.eventCount + ' matching events';
      if (this.isAdd) {
        return 'Add tag "' + this.tag + '" to all ' + countStr + ' from this device?';
      }
      return 'Remove tag "' + this.tag + '" from all ' + countStr + ' from this device?';
    },
    deviceOnlyButtonText() {
      return 'Device Only';
    },
    allEventsButtonText() {
      var countStr = this.eventCount === 1 ? '1 Event' : 'All ' + this.eventCount + ' Events';
      return this.isAdd ? 'Apply to ' + countStr : 'Remove from ' + countStr;
    }
  },
  methods: {
    handleChoice(propagate) {
      this.$emit('respond', { propagate: propagate, dontAskAgain: this.dontAskAgain });
      this.$emit('input', false);
    }
  }
};
</script>
