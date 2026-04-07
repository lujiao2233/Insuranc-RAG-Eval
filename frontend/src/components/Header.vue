<template>
  <div class="header">
    <h1>{{ title }}</h1>
    <div class="user-actions">
      <el-dropdown v-if="isLoggedIn" @command="handleCommand">
        <span class="el-dropdown-link">
          {{ userInfo.username }} <el-icon><arrow-down /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">个人资料</el-dropdown-item>
            <el-dropdown-item command="settings">设置</el-dropdown-item>
            <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <div v-else>
        <el-button type="primary" @click="goToLogin">登录</el-button>
        <el-button @click="goToRegister">注册</el-button>
      </div>
    </div>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'

export default {
  name: 'Header',
  setup() {
    return {
      ArrowDown
    }
  },
  data() {
    return {
      title: 'RAG 评估系统',
      isLoggedIn: false,
      userInfo: {
        username: ''
      }
    }
  },
  methods: {
    handleCommand(command) {
      switch(command) {
        case 'logout':
          this.logout()
          break
        case 'profile':
          // 跳转到个人资料页面
          this.$router.push('/profile')
          break
        case 'settings':
          // 跳转到设置页面
          this.$router.push('/settings')
          break
      }
    },
    logout() {
      // 清除用户信息
      this.isLoggedIn = false
      this.userInfo = { username: '' }
      
      // 跳转到登录页
      this.$router.push('/login')
      
      ElMessage.success('已成功退出登录')
    },
    goToLogin() {
      this.$router.push('/login')
    },
    goToRegister() {
      this.$router.push('/register')
    }
  },
  mounted() {
    // 检查用户是否已登录
    const token = localStorage.getItem('access_token')
    if (token) {
      this.isLoggedIn = true
      // 这里应该调用API获取用户信息
      this.userInfo = { username: 'demo_user' } // 示例数据
    }
  }
}
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.el-dropdown-link {
  cursor: pointer;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 5px;
}
</style>