import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '@/views/LandingPage.vue'
import Dashboard from "@/views/Dashboard.vue";
import ProfilePage from "@/views/ProfilePage.vue";
import Settings from "@/views/Settings.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'Landing', component: LandingPage },
    { path: '/dashboard', name: 'Dashboard', component: Dashboard },
    { path: '/profile/:username', name: 'Profile', component: ProfilePage },
    { path: '/settings', name: 'Settings', component: Settings },
  ]
})

export default router
