<template>
  <div>
    <v-card class="d-flex align-start mb-1" id="tsSearchBar" outlined>
      <v-text-field
        v-model="currentQueryString"
        hide-details
        label="Search"
        placeholder="Search"
        single-line
        dense
        flat
        solo
        class="pa-2"
        id="tsSearchInput"
        @keyup.enter="search()"
        ref="searchInput"
      >
        <template v-slot:append>
          <v-icon title="Run search" @click="search()" class="mr-3">mdi-magnify</v-icon>
          <v-icon title="Show search examples" id="tsSearchHelpButton" @click="showSearchHelp = true">mdi-help-circle-outline</v-icon>
        </template>
      </v-text-field>
    </v-card>

    <!-- Search Help Dialog -->
    <v-dialog v-model="showSearchHelp" max-width="1800" scrollable>
      <search-help-card :flat="true" @close-dialog="showSearchHelp = false"></search-help-card>
    </v-dialog>
  </div>
</template>

<script>
import SearchHelpCard from './SearchHelpCard.vue'

export default {
  name: 'SearchBar',
  components: {
    SearchHelpCard,
  },
  props: {
    value: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      currentQueryString: this.value,
      showSearchHelp: false,
    }
  },
  watch: {
    value(newVal) {
      this.currentQueryString = newVal
    },
  },
  mounted() {
    this.$nextTick(function () {
      if (this.$refs.searchInput) {
        this.$refs.searchInput.focus()
      }
    }.bind(this))
  },
  methods: {
    search() {
      this.$emit('input', this.currentQueryString)
      this.$emit('search', {
        queryString: this.currentQueryString,
      })
    },
  },
}
</script>
