<template>
  <v-dialog v-model="internalValue" :max-width="maxWidth">
    <v-card>
      <v-card-title>
        {{ title }}
      </v-card-title>
      <v-card-text>
        <pre class="json-content">{{ JSON.stringify(data, null, 2) }}</pre>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn text @click="internalValue = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: 'JSONModal',
  props: {
    value: {
      type: Boolean,
      default: false
    },
    title: {
      type: String,
      required: true
    },
    data: {
      type: [Object, Array],
      required: true
    },
    maxWidth: {
      type: String,
      default: '800'
    }
  },
  computed: {
    internalValue: {
      get() {
        return this.value
      },
      set(val) {
        this.$emit('input', val)
      }
    }
  }
}
</script>

<style scoped>
.json-content {
  max-height: 600px;
  overflow: auto;
  background: white;
  border: 1px solid #bdbdbd;
  padding: 16px;
  border-radius: 4px;
  font-size: 14px;
  color: #212121;
  line-height: 2;
  font-family: Menlo, Monaco, 'Courier New', monospace;
}
</style>
