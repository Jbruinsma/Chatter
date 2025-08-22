<!-- src/components/FollowingList.vue -->
<template>
  <div class="following-list">
    <h3>Following</h3>
    <ul>
      <li v-for="following in followingList" :key="following">{{ following }}</li>
    </ul>
  </div>
</template>

<script setup>
defineProps({
  followingList: {
    type: Array,
    required: true,
  },
})
</script>

<style scoped>
.following-list { margin-top: 1rem; }
</style>

