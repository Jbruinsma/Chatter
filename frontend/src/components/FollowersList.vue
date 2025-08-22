<template>
  <div class="followers-list">
    <h3>Followers</h3>
    <ul>
      <li v-for="follower in followers" :key="follower">{{ follower }}</li>
    </ul>
  </div>
</template>

<script setup>
defineProps({
  followers: {
    type: Array,
    required: true,
  },
})
</script>

<style scoped>
.followers-list { border-bottom: 1px solid #333; margin-bottom: 1rem; padding-bottom: 1rem; }
</style>
