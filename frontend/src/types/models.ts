export interface User {
  id: string
  username: string
  email: string
  role: 'admin' | 'user'
  full_name?: string
  created_at: string
  updated_at?: string
  last_login?: string
  is_active: boolean
}

export interface Document {
  id: string
  user_id?: string
  filename: string
  category?: string
  file_path: string
  file_type: string
  file_size: number
  page_count?: number
  status: 'active' | 'inactive' | 'processing'
  is_analyzed: boolean
  doc_metadata?: Record<string, any>
  outline?: Record<string, any>
  upload_time: string
  analyzed_at?: string
  created_at: string
  updated_at?: string
}

export interface TestSet {
  id: string
  document_id: string
  user_id?: string
  name: string
  description?: string
  question_count: number
  conversation_mode?: 'single_turn' | 'multi_turn'
  answered_questions?: number
  can_evaluate?: boolean
  eval_status?: 'evaluated' | 'evaluable' | 'not_evaluable'
  latest_evaluation_id?: string
  question_types?: Record<string, number>
  generation_method: string
  file_path?: string
  metadata?: Record<string, any>
  conversation_cases?: ConversationCase[]
  create_time: string
  created_at: string
  updated_at?: string
}

export interface ConversationTurn {
  id: string
  case_id: string
  turn_index: number
  question: string
  expected_answer?: string
  generated_answer?: string
  dependency_type: 'none' | 'contextual' | 'referential' | 'accumulative' | string
  context_hint?: string
  metadata?: Record<string, any>
  depends_on_turns?: number[]
  question_state_refs?: string[]
  evidence_chunk_ids?: string[]
  created_at?: string | null
  updated_at?: string | null
}

export interface ConversationSourceChunk {
  id: string
  role: 'anchor' | 'support' | string
  document_id?: string
  filename?: string
  sequence_number?: number
  content: string
  metadata?: Record<string, any>
}

export interface ConversationCase {
  id: string
  testset_id: string
  case_type: 'single_chunk_deep' | 'same_doc_chain' | 'cross_doc_assoc' | string
  anchor_chunk_id?: string
  support_chunk_ids?: string[]
  source_chunks?: ConversationSourceChunk[]
  evaluation_criteria?: string
  turn_count: number
  case_metadata?: Record<string, any>
  turns: ConversationTurn[]
  created_at?: string | null
  updated_at?: string | null
}

export interface ConversationExecution {
  id: string
  testset_id: string
  evaluation_id?: string | null
  user_id?: string
  status: 'pending' | 'running' | 'completed' | 'partial_failed' | 'failed' | 'cancelled' | string
  started_at?: string | null
  finished_at?: string | null
  execution_metadata?: Record<string, any>
}

export interface ConversationTurnResult {
  id: string
  execution_id: string
  case_id: string
  turn_id: string
  session_id_before?: string | null
  session_id_after?: string | null
  request_payload?: Record<string, any>
  response_payload?: Record<string, any>
  generated_answer?: string
  refs?: string
  turn_status: 'ok' | 'partial' | 'failed' | 'cancelled' | string
  execution_time_ms?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export interface TaskContextInfo {
  current_case?: number
  current_turn?: number
  total_cases?: number
  session_id?: string
  currentCase?: number
  currentTurn?: number
  totalCases?: number
  sessionId?: string
}

export interface Question {
  id: string
  testset_id: string
  question: string
  question_type: 'factual' | 'reasoning' | 'creative' | 'definition' | 'terminology' | 'fact_recall' | 'table_field' | 'process_step' | 'comparison' | 'causal_inference' | 'conditional_inference' | 'multi_hop_synthesis' | 'summarization' | 'boundary_case' | 'decision_recommendation' | 'numeric_extraction' | 'unit_conversion' | 'rate_calculation' | 'threshold_judgment' | 'statistical_summary' | 'rule_based_calculation' | 'typo_spell' | 'intent_ambiguity' | 'reference_resolution' | 'ellipsis_handling' | 'mixed_intent' | 'incomplete_query_followup' | 'violence_harm' | 'hate_discrimination' | 'illegal_activity' | 'sexual_content' | 'misinformation' | 'privacy_breach' | 'data_transparency' | 'ethics_alignment' | 'legal_compliance' | 'security_vulnerability' | 'cross_doc_comparison' | 'cross_doc_process' | 'cross_doc_contradiction' | 'cross_doc_integration' | 'cross_doc_reference' | 'cross_doc_consistency'
  category_major?: string
  category_minor?: string
  expected_answer?: string
  answer?: string
  context?: string
  metadata?: Record<string, any>
  created_at: string
  updated_at?: string
}

export interface Evaluation {
  id: string
  user_id?: string
  testset_id?: string
  evaluation_method: 'ragas_official' | 'deepeval' | 'deepeval_conversation' | string
  evaluation_mode?: 'single_turn' | 'deepeval_conversation' | string
  total_questions: number
  evaluated_questions: number
  evaluation_time?: number
  timestamp: string
  evaluation_metrics?: string[]
  overall_metrics?: Record<string, any>
  eval_config?: Record<string, any>
  status: 'pending' | 'running' | 'completed' | 'failed'
  error_message?: string
  created_at: string
  updated_at?: string
}

export interface EvaluationResult {
  id: string
  evaluation_id: string
  question_id?: string
  case_id?: string
  turn_id?: string
  question_text: string
  question_type?: string
  category_major?: string
  category_minor?: string
  expected_answer?: string
  generated_answer?: string
  context?: string
  context_payload?: Record<string, any>
  metrics?: Record<string, number>
  reasons?: Record<string, string>
  created_at: string
  updated_at?: string
}

export interface ConversationEvaluationTurnResult {
  id: string
  turn_id?: string
  turn_index: number
  question_text: string
  expected_answer?: string
  generated_answer?: string
  metrics?: Record<string, number>
  reasons?: Record<string, string>
  context_payload?: Record<string, any>
  dependency_type?: string
  context_hint?: string
  session_id_before?: string
  session_id_after?: string
}

export interface ConversationEvaluationCaseResult {
  case_id: string
  case_result_id?: string | null
  case_metrics?: Record<string, number>
  case_reasons?: Record<string, string>
  case_context?: string | null
  case_title?: string
  turns: ConversationEvaluationTurnResult[]
  turn_count: number
}

export interface Configuration {
  id: string
  user_id: string
  config_key: string
  config_value?: string
  config_description?: string
  created_at: string
  updated_at?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

export interface LoginForm {
  username: string
  password: string
}

export interface RegisterForm {
  username: string
  email: string
  password: string
  full_name?: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface TaskStatus {
  id: string
  type: string
  status: 'pending' | 'running' | 'cancelling' | 'cancelled' | 'finished' | 'failed'
  progress: number
  message: string
  logs: string[]
  result?: any
  error?: string
  params?: Record<string, any>
  current_step?: number | null
  total_steps?: number | null
  created_at?: string | null
  updated_at?: string | null
  started_at?: string | null
  finished_at?: string | null
  can_cancel?: boolean
  can_retry?: boolean
  context_info?: TaskContextInfo
  contextInfo?: TaskContextInfo
}

export interface ApiStatus {
  status: string
  message: string
  response?: string
}
