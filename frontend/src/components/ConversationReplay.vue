<template>
  <div class="conversation-replay">
    <div v-if="orderedTurns.length === 0" class="empty-state">
      <el-empty description="暂无会话回放数据" :image-size="60" />
    </div>

    <div v-else class="turn-list">
      <div v-for="turn in orderedTurns" :key="turn.id || turn.turn_id || turn.turn_index" class="turn-row">
        <div class="turn-label">Turn {{ turn.turn_index }}</div>
        <div class="turn-content">
          <div class="question-panel">
            <div class="panel-header">
              <span>用户问题</span>
              <el-tag v-if="turn.dependency_type" size="small" type="info">{{ turn.dependency_type }}</el-tag>
            </div>
            <div class="panel-text">{{ turn.question_text || '-' }}</div>
            <div v-if="turn.context_hint" class="panel-hint">{{ turn.context_hint }}</div>
          </div>

          <div class="answer-panel">
            <div class="panel-header">
              <span>模型回答</span>
              <el-tag size="small" :type="getMetricType(turn.metrics?.conversation_relevancy)">
                相关性 {{ formatMetric(turn.metrics?.conversation_relevancy) }}
              </el-tag>
            </div>
            <div class="panel-text">{{ turn.generated_answer || '-' }}</div>
            <div v-if="showMetrics && turn.metrics && Object.keys(turn.metrics).length > 0" class="metric-tags">
              <el-tag
                v-for="(value, key) in turn.metrics"
                :key="key"
                :type="getMetricType(value)"
                size="small"
              >
                {{ getMetricName(key) }}: {{ formatMetric(value) }}
              </el-tag>
            </div>
            <div v-if="showReasons && turn.reasons && Object.keys(turn.reasons).length > 0" class="reason-list">
              <div v-for="(reason, key) in turn.reasons" :key="key" class="reason-item">
                <el-tag size="small" type="info">{{ getMetricName(key) }}</el-tag>
                <span class="reason-text">{{ reason }}</span>
              </div>
            </div>
            <div v-if="resolveRefs(turn).length > 0" class="refs-list">
              <div class="refs-title">引用来源</div>
              <div v-for="(refText, idx) in resolveRefs(turn)" :key="idx" class="ref-item">{{ refText }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="orderedTurns.length > 0" class="session-timeline">
      <div class="timeline-title">SessionId 变化时间线</div>
      <div class="timeline-list">
        <div v-for="turn in orderedTurns" :key="`session-${turn.id || turn.turn_id || turn.turn_index}`" class="timeline-item">
          <span class="timeline-turn">Turn {{ turn.turn_index }}</span>
          <el-tag size="small" type="info">{{ turn.session_id_before || '-' }}</el-tag>
          <span class="timeline-arrow">-></span>
          <el-tag size="small" type="success">{{ turn.session_id_after || '-' }}</el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ConversationEvaluationTurnResult } from '@/types'

interface Props {
  turns: ConversationEvaluationTurnResult[]
  showMetrics?: boolean
  showReasons?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  turns: () => [],
  showMetrics: true,
  showReasons: true
})

const orderedTurns = computed(() => {
  return [...props.turns].sort((a, b) => (a.turn_index || 0) - (b.turn_index || 0))
})

const formatMetric = (value?: number) => {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(3) : '-'
}

const getMetricType = (value?: number) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 'info'
  if (value >= 0.8) return 'success'
  if (value >= 0.6) return 'warning'
  return 'danger'
}

const getMetricName = (key: string) => {
  const metricNames: Record<string, string> = {
    knowledge_retention: 'Knowledge Retention',
    conversation_relevancy: 'Conversation Relevancy',
    conversation_completeness: 'Conversation Completeness',
    role_adherence: 'Role Adherence'
  }
  return metricNames[key] || key
}

const resolveRefs = (turn: ConversationEvaluationTurnResult): string[] => {
  const payload = turn.context_payload || {}
  const refs = payload.refs
  if (Array.isArray(refs)) {
    return refs.map(item => String(item).trim()).filter(Boolean)
  }
  if (typeof refs === 'string' && refs.trim()) {
    return refs.split('\n').map(line => line.trim()).filter(Boolean)
  }
  return []
}
</script>

<style scoped lang="scss">
.conversation-replay {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.turn-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.turn-row {
  border: 1px solid var(--border-1, #ebeef5);
  border-radius: var(--radius-8, 8px);
  padding: 12px;
  background: var(--bg-card, #fff);
}

.turn-label {
  font-size: var(--font-13, 13px);
  font-weight: var(--fw-600, 600);
  color: var(--text-2, #606266);
  margin-bottom: 10px;
}

.turn-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.question-panel,
.answer-panel {
  border: 1px solid var(--border-1, #ebeef5);
  border-radius: var(--radius-8, 8px);
  padding: 10px;
  background: var(--bg-app, #f8fafc);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: var(--font-13, 13px);
  color: var(--text-2, #606266);
}

.panel-text {
  font-size: var(--font-14, 14px);
  color: var(--text-1, #303133);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.panel-hint {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--border-1, #dcdfe6);
  font-size: var(--font-12, 12px);
  color: var(--text-2, #909399);
}

.metric-tags {
  margin-top: 10px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.reason-list {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.reason-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.reason-text {
  font-size: var(--font-12, 12px);
  color: var(--text-2, #606266);
  line-height: 1.5;
}

.refs-list {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--border-1, #dcdfe6);
}

.refs-title {
  font-size: var(--font-12, 12px);
  color: var(--text-2, #909399);
  margin-bottom: 4px;
}

.ref-item {
  font-size: var(--font-12, 12px);
  color: var(--text-2, #606266);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.session-timeline {
  border: 1px solid var(--border-1, #ebeef5);
  border-radius: var(--radius-8, 8px);
  padding: 10px 12px;
  background: var(--bg-app, #f8fafc);
}

.timeline-title {
  font-size: var(--font-13, 13px);
  color: var(--text-2, #606266);
  margin-bottom: 8px;
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.timeline-item {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.timeline-turn {
  color: var(--text-2, #606266);
  font-size: var(--font-12, 12px);
}

.timeline-arrow {
  color: var(--text-3, #b4bccc);
}

@media (max-width: 992px) {
  .turn-content {
    grid-template-columns: 1fr;
  }
}
</style>
