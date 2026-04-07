<template>
  <div class="reports-view">
    <el-card>
      <template #header>
        <span>报告中心</span>
      </template>
      
      <el-table
        v-loading="loading"
        :data="reports"
        style="width: 100%"
      >
        <el-table-column prop="evaluation_id" label="评估ID" width="200">
          <template #default="{ row }">
            {{ row.evaluation_id.substring(0, 8) }}...
          </template>
        </el-table-column>
        <el-table-column prop="testset_name" label="测试集" min-width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text @click="viewReport(row.evaluation_id)">
              查看
            </el-button>
            <el-button type="success" text @click="generateReport(row.evaluation_id, 'html')">
              HTML
            </el-button>
            <el-button type="warning" text @click="generateReport(row.evaluation_id, 'pdf')">
              PDF
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { reportApi, type Report } from '@/api/reports'
import { formatDateTime } from '@/utils/format'

const router = useRouter()

const loading = ref(false)
const reports = ref<Report[]>([])

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    completed: 'success',
    pending: 'info',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    completed: '已完成',
    pending: '待生成',
    failed: '失败'
  }
  return texts[status] || status
}

const fetchReports = async () => {
  loading.value = true
  try {
    const response = await reportApi.getReports()
    reports.value = response.items
  } catch (error) {
    ElMessage.error('获取报告列表失败')
  } finally {
    loading.value = false
  }
}

const viewReport = (evaluationId: string) => {
  router.push(`/reports/${evaluationId}`)
}

const generateReport = async (evaluationId: string, format: 'pdf' | 'html') => {
  try {
    const result = await reportApi.generateReport(evaluationId, format)
    ElMessage.success(result.message)
    
    if (format === 'pdf') {
      const blob = await reportApi.downloadReport(evaluationId, 'pdf')
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `report_${evaluationId.substring(0, 8)}.pdf`
      a.click()
      window.URL.revokeObjectURL(url)
    }
  } catch (error) {
    ElMessage.error('生成报告失败')
  }
}

onMounted(() => {
  fetchReports()
})
</script>

<style lang="scss" scoped>
.reports-view {
  // 样式
}
</style>
