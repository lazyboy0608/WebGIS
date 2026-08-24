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
