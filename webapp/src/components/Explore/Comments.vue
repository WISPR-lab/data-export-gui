<!--
Copyright 2023 Google Inc. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->
<template>
  <v-card outlined>
    <v-toolbar dense flat>
      <v-toolbar-title style="font-size: 1.2em">Comments</v-toolbar-title>
    </v-toolbar>

    <v-list three-line>
      <v-list-item
        v-for="(comment, index) in comments"
        :key="comment.id"
        @mouseover="selectComment(comment)"
        @mouseleave="unSelectComment()"
      >
        <v-list-item-avatar>
          <v-avatar color="grey lighten-1">
            <span class="white--text">{{ comment.user.username | initialLetter }}</span>
          </v-avatar>
        </v-list-item-avatar>

        <v-list-item-content>
          <v-list-item-title>
            {{ comment.user.username }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ comment.created_at | shortDateTime }} ({{ comment.created_at | timeSince }})
          </v-list-item-subtitle>

          <v-card flat v-if="comment.editable" class="mt-5">
            <v-textarea v-model="comments[index].comment" hide-details auto-grow filled></v-textarea>

            <v-card-actions v-if="comment.editable">
              <v-spacer></v-spacer>
              <v-btn text color="primary" v-if="comment.editable" @click="editComment(index, false)"> Cancel </v-btn>
              <v-btn text color="primary" @click="updateComment(comment, index)"> Save </v-btn>
            </v-card-actions>
          </v-card>
          <p v-else style="max-width: 90%" class="body-2">{{ comment.comment }}</p>
        </v-list-item-content>

        <v-list-item-action
          v-if="comment === selectedComment && currentUser == comment.user.username"
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
        v-model="comment"
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
import DB from '@/database/index.js'

export default {
  props: ['event', 'currentSearchNode'],
  data() {
    return {
      comment: '',
      comments: [],
      selectedComment: false,
    }
  },
  computed: {
    currentUser() {
      return this.$store.state.currentUser
    },
    formattedComments() {
      return this.comments || []
    }
  },
  watch: {
    event: {
      handler(newVal) {
        if (newVal && newVal._id) {
          this.fetchComments()
        }
      },
      immediate: true
    }
  },
  methods: {
    async fetchComments() {
      try {
        if (!this.event || !this.event._id) return
        this.comments = await pyDB.getEventComments(this.event._id)
      } catch (e) {
        console.error('Failed to load comments', e)
      }
    },
    async postComment() {
      if (!this.comment.trim()) return
      
      try {
        await pyDB.addEventComment(this.event._id, this.comment)
        this.comment = ''
        await this.fetchComments() // Refresh list
      } catch (e) {
        console.error('Failed to post comment', e)
      }
    },
    async updateComment(comment, commentIndex) {
      try {
        await pyDB.updateEventComment(comment.id, comment.comment)
        comment.editable = false
        comment.updated_at = new Date().toISOString()
        this.comments.splice(commentIndex, 1, comment)
      } catch (e) {
        console.error('Error updating comment:', e)
      }
    },
    async deleteComment(commentId, commentIndex) {
      if (!confirm('Are you sure?')) return
      
      try {
        await pyDB.deleteEventComment(commentId)
        this.comments.splice(commentIndex, 1)
        this.$store.dispatch('updateEventLabels', { label: "__ts_comment", num: -1 })
      } catch (e) {
        console.error('Error deleting comment:', e)
      }
    },
    editComment(commentIndex, enable = true) {
      const changeComment = this.comments[commentIndex]
      changeComment.editable = enable
      this.comments.splice(commentIndex, 1, changeComment)
    },
    selectComment(comment) {
      this.selectedComment = comment
    },
    unSelectComment() {
      this.selectedComment = false
    },
  },
}
</script>
