<template>
  <div class="page reports-page">
    <el-card shadow="never" class="section" :body-style="{ padding: '16px' }">
      <template #header>
        <span class="page-title">报告中心</span>
      </template>
      
      <el-table
        v-loading="loading"
        :data="reports"
        style="width: 100%"
        size="small"
      >
        <el-table-column prop="testset_name" label="测试集" min-width="150">
          <template #default="{ row }">
            <el-link type="primary" @click="viewReport(row.evaluation_id)">
              {{ row.testset_name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at || row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="button-row">
              <el-button link type="primary" size="small" @click="viewReport(row.evaluation_id)">
                查看
              </el-button>
              <el-button link type="primary" size="small" @click="downloadReport(row.evaluation_id, 'html')">
                HTML
              </el-button>
              <el-button link type="primary" size="small" @click="exportScoredTestset(row)">
                导出
              </el-button>
              <el-button link type="danger" size="small" @click="handleDelete(row.evaluation_id)">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { reportApi, type Report } from '@/api/reports'
import { testsetApi } from '@/api/testsets'
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

const downloadReport = async (evaluationId: string, format: 'pdf' | 'html') => {
  try {
    const blob = await reportApi.downloadReport(evaluationId, format)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${evaluationId.substring(0, 8)}.${format}`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

const exportScoredTestset = async (report: Report) => {
  if (!report.testset_id) {
    ElMessage.error('缺少测试集信息，无法导出')
    return
  }
  try {
    const blob = await testsetApi.exportTestSet(report.testset_id, {
      evaluation_id: report.evaluation_id
    })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${(report.testset_name || 'testset').replace(/\s+/g, '_')}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

const handleDelete = async (evaluationId: string) => {
  try {
    await ElMessageBox.confirm('确定要删除该报告吗？删除后不可恢复。', '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await reportApi.deleteReport(evaluationId)
    ElMessage.success('删除成功')
    await fetchReports()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  fetchReports()
})
</script>

<style lang="scss" scoped>
.reports-page {
  .page-title {
    font-size: var(--font-16, 16px);
    font-weight: var(--fw-600, 600);
    color: var(--text-1, #303133);
  }

  .button-row {
    display: flex;
    gap: 8px;
    align-items: center;
  }
}

:deep(.el-card__header) {
  padding: 16px;
  border-bottom: 1px solid var(--border-1, #ebeef5);
}

:deep(.el-table) {
  --el-table-header-bg-color: var(--bg-app, #f8fafc);
  --el-table-header-text-color: var(--text-2, #606266);
  border-radius: var(--radius-8, 8px);
  overflow: hidden;
  
  th.el-table__cell {
    font-weight: 500;
  }
}
</style>
