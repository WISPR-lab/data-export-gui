<template>
  <v-card outlined>
    <v-toolbar dense flat>
      <v-toolbar-title style="font-size: 1.2em">Comments</v-toolbar-title>
    </v-toolbar>

    <v-list three-line>
      <v-list-item
        v-for="(comment, index) in device.comments"
        :key="comment.id"
        @mouseover="selectComment(comment)"
        @mouseleave="unSelectComment()"
      >
        <v-list-item-avatar>
          <v-avatar color="grey lighten-1">
            <span class="white--text">L</span>
          </v-avatar>
        </v-list-item-avatar>

        <v-list-item-content>
          <v-list-item-title>
            local-user
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ comment.created_at | shortDateTime }} ({{ comment.created_at | timeSince }})
          </v-list-item-subtitle>

          <v-card flat v-if="comment.editable" class="mt-5">
            <v-textarea v-model="device.comments[index].content" hide-details auto-grow filled></v-textarea>

            <v-card-actions v-if="comment.editable">
              <v-spacer></v-spacer>
              <v-btn text color="primary" @click="editComment(index, false)"> Cancel </v-btn>
              <v-btn text color="primary" @click="updateComment(comment, index)"> Save </v-btn>
            </v-card-actions>
          </v-card>
          <p v-else style="max-width: 90%" class="body-2">{{ comment.content }}</p>
        </v-list-item-content>

        <v-list-item-action
          v-if="comment === selectedComment"
          style="position: absolute; right: 0"
        >
          <v-chip outlined style="margin-right: 10px">
            <v-btn icon small @click="editComment(index)">
              <v-icon title="Edit comment" small>mdi-square-edit-outline</v-icon>
            </v-btn>
            <v-btn icon small @click="deleteComment(comment.id, index)">
              <v-icon title="Delete comment" small>mdi-trash-can-outline</v-icon>
            </v-btn>
          </v-chip>
        </v-list-item-action>
      </v-list-item>
    </v-list>

    <v-card-actions>
      <v-textarea
        v-model="newComment"
        hide-details
        auto-grow
        filled
        class="mx-2 mb-2"
        label="Add comment"
        rows="1"
      ></v-textarea>
      <v-btn icon @click="postComment">
        <v-icon title="Submit comment">mdi-send</v-icon>
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
export default {
  name: 'DeviceComments',
  props: {
    device: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      newComment: '',
      selectedComment: null,
    }
  },
  filters: {
    shortDateTime(timestamp) {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    },
    timeSince(timestamp) {
      if (!timestamp) return ''
      const now = Date.now()
      const diff = now - timestamp
      const minutes = Math.floor(diff / 60000)
      const hours = Math.floor(diff / 3600000)
      const days = Math.floor(diff / 86400000)
      
      if (minutes < 1) return 'just now'
      if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`
      if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`
      return `${days} day${days > 1 ? 's' : ''} ago`
    },
  },
  methods: {
    selectComment(comment) {
      this.selectedComment = comment
    },
    unSelectComment() {
      this.selectedComment = null
    },
    editComment(index, enable = true) {
      this.$set(this.device.comments[index], 'editable', enable)
    },
    updateComment(comment, index) {
      this.$set(this.device.comments[index], 'editable', false)
      this.$emit('update-comment-text', { deviceId: this.device.id, index, text: comment.content })
    },
    deleteComment(commentId, index) {
      this.$emit('delete-comment', { deviceId: this.device.id, index })
    },
    postComment() {
      if (this.newComment.trim()) {
        const comment = {
          id: Date.now(),
          content: this.newComment,
          created_at: Date.now(),
          editable: false,
        }
        if (!this.device.comments) {
          this.device.comments = []
        }
        this.device.comments.push(comment)
        this.newComment = ''
      }
    },
  },
}
</script>

<style scoped lang="scss">
</style>
