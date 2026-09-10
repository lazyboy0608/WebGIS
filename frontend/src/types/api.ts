export type Geometry = {
  type: string
  coordinates: unknown
}

export type GeoJSONFeature = {
  type: 'Feature'
  geometry: Geometry | null
  properties: Record<string, unknown>
}

export type GeoJSONFeatureCollection = {
  type: 'FeatureCollection'
  features: GeoJSONFeature[]
}

export type FileListItem = {
  id: number
  filename: string
  source_crs: string
  trace_count: number
  line_count: number
  processed_line_count: number
  processed_shot_point_count: number
  processed_trace_count: number
  has_processed_data: boolean
  label?: string
  color?: string
  status?: 'ready' | 'partial' | 'empty'
}

export type FileListResponse = {
  items: FileListItem[]
  total: number
  offset: number
  limit: number
}

export type ProcessedDataSummary = Omit<FileListItem, 'has_processed_data'> & {
  id: number
  filename: string
}

export type LayerData = {
  lines: GeoJSONFeatureCollection
  shotPoints: GeoJSONFeatureCollection
  traces: GeoJSONFeatureCollection
}

export type BatchDeleteResponse = {
  deleted_ids: number[]
  count: number
}

export type SeismicBlock = {
  id: number
  block_code: string
  operator: string | null
  basin_name: string | null
  area_km2: number | null
  status: 'active' | 'split'
  parent_id: number | null
  source_file: string | null
  created_at: string
  updated_at?: string
}

export type BlockUploadResponse = {
  message: string
  imported_count: number
  blocks: SeismicBlock[]
}

export type BlockSplitRequest = {
  split_line_wkt: string
  new_block_codes?: string[]
}

/**
 * Command Pattern — một phần tử trong Undo/Redo Stack.
 * Lưu đủ thông tin để gọi API undo-split VÀ re-execute (redo) split.
 */
export type SplitCommand = {
  /** ID của lô cha (đã bị đổi sang status='split') */
  parentBlockId: number
  /** Mã lô cha để hiển thị trong tooltip nút Undo */
  parentBlockCode: string
  /** IDs của 2 lô con vừa được tạo */
  childIds: number[]
  /** WKT LineString dùng để tách — cần cho Redo (re-execute) */
  splitLineWkt: string
  /** Tên các lô con — cần cho Redo */
  newBlockCodes: string[]
}

/** Response từ POST /api/blocks/undo-split */
export type UndoSplitResponse = {
  restored_block: SeismicBlock
  deleted_child_ids: number[]
}

export type SegyTaskStatusResponse = {
  task_id: string
  filename: string
  status: string
  progress_percent: number
  message: string
  result?: any
  error?: string
  created_at?: string
  updated_at?: string
}

export type SegyHeaderInspectionResult = {
  filename: string
  source_crs: string
  source_crs_name: string
  default_target_crs: string
  default_target_crs_name: string
  trace_count: number
  textual_header_preview?: string | null
}

export type CrsPreset = {
  code: string
  name: string
  description?: string | null
  category?: string | null
}

