<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

onMounted(() => {
  if (authStore.token && !authStore.user) {
    authStore.fetchCurrentUser()
  }
})
</script>

<style lang="scss">
#app {
  width: 100%;
  height: 100%;
}
</style>
