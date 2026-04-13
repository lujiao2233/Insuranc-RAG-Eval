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
            {{ formatDateTime(row.created_at || row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <div class="button-row">
              <el-button type="primary" size="small" class="fixed-width-btn" @click="viewReport(row.evaluation_id)">
                查看
              </el-button>
              <el-button type="success" size="small" class="fixed-width-btn" @click="downloadReport(row.evaluation_id, 'html')">
                HTML
              </el-button>
            </div>
            <div class="button-row">
              <el-button type="warning" size="small" class="fixed-width-btn" @click="downloadReport(row.evaluation_id, 'pdf')">
                PDF
              </el-button>
              <el-button type="danger" size="small" class="fixed-width-btn" @click="handleDelete(row.evaluation_id)">
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
.reports-view {
  .button-row {
    display: flex;
    gap: 8px;
    margin-bottom: 6px;
  }
  .fixed-width-btn {
    width: 80px;
    justify-content: center;
  }
}
</style>
