export interface ApiResponse<T = any> {
  data: T
  message?: string
  success?: boolean
}

export interface ApiError {
  detail: string
  status_code?: number
}

export interface ListParams {
  skip?: number
  limit?: number
  page?: number
  size?: number
}

export interface DocumentQuery extends ListParams {
  status?: string
  is_analyzed?: boolean
}

export interface EvaluationQuery extends ListParams {
  status?: string
  testset_id?: string
}

export interface ReportQuery extends ListParams {
  evaluation_id?: string
}
