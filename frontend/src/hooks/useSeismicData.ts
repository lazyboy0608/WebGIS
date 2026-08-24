import { startTransition, useEffect, useState } from 'react'
import type {
  BatchDeleteResponse,
  FileListItem,
  FileListResponse,
  GeoJSONFeatureCollection,
  LayerData,
  ProcessedDataSummary,
} from '../types/api'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8001').replace(/\/$/, '')
const PROCESSING_API_BASE_URL = (import.meta.env.VITE_PROCESSING_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

function withUiFields(file: FileListItem): FileListItem {
  const hasLines = file.processed_line_count > 0
  const hasPoints = file.processed_shot_point_count > 0 || file.processed_trace_count > 0
  return {
    ...file,
    label: `${file.filename} (#${file.id})`,
    color: hasLines ? '#e4572e' : hasPoints ? '#1d7a8c' : '#8b949e',
    status: hasLines && hasPoints ? 'ready' : hasLines || hasPoints ? 'partial' : 'empty',
  }
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const url = `${API_BASE_URL}${path}`
  try {
    for (let attempt = 0; attempt < 5; attempt += 1) {
      const response = await fetch(url, { signal })
      if (response.ok) return response.json() as Promise<T>
      if (response.status !== 404 || attempt === 4) {
        throw new Error(`Request failed (${response.status}) at ${path}`)
      }
      await new Promise((resolve) => window.setTimeout(resolve, 250))
    }
    throw new Error(`Request failed (404) at ${path}`)
  } catch (reason) {
    if (reason instanceof DOMException && reason.name === 'AbortError') throw reason
    if (reason instanceof TypeError) {
      throw new Error(`Không thể kết nối Backend 2 tại ${API_BASE_URL}`, { cause: reason })
    }
    throw reason
  }
}

export function useSeismicData(fileIds: number[]) {
  const [files, setFiles] = useState<FileListItem[]>([])
  const [summary, setSummary] = useState<ProcessedDataSummary | null>(null)
  const [layers, setLayers] = useState<LayerData | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filesRefreshToken, setFilesRefreshToken] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    startTransition(() => setLoading(true))
    getJson<FileListResponse>('/api/segy-files?offset=0&limit=500', controller.signal)
      .then((payload) => setFiles(payload.items.map(withUiFields)))
      .catch((reason: unknown) => {
        if ((reason as Error).name !== 'AbortError') setError((reason as Error).message || 'Không thể tải danh sách SEG-Y')
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [filesRefreshToken])

  async function uploadFiles(files: File[], sourceCrs?: string): Promise<number[]> {
    if (files.length === 0) return []
    if (files.some((file) => !file.name.toLowerCase().endsWith('.sgy'))) {
      throw new Error('Chỉ hỗ trợ file SEG-Y có phần mở rộng .sgy')
    }

    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    if (sourceCrs) formData.append('source_crs', sourceCrs)
    setUploading(true)
    setError(null)

    try {
      const endpoint = files.length === 1 ? '/api/segy-files/upload' : '/api/segy-files/upload/batch'
      if (files.length === 1) {
        formData.delete('files')
        formData.append('file', files[0])
      }
      const response = await fetch(`${PROCESSING_API_BASE_URL}${endpoint}`, {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) throw new Error(`Backend 1 từ chối upload (${response.status})`)
      const result = await response.json() as { segy_file_id?: number; files?: { segy_file_id: number }[] }
      setFilesRefreshToken((token) => token + 1)
      return result.segy_file_id !== undefined
        ? [result.segy_file_id]
        : (result.files ?? []).map((file) => file.segy_file_id)
    } catch (reason) {
      const message = reason instanceof TypeError
        ? `Không thể kết nối Backend 1 tại ${PROCESSING_API_BASE_URL}`
        : reason instanceof Error ? reason.message : 'Không thể upload file SEG-Y'
      setError(message)
      throw reason
    } finally {
      setUploading(false)
    }
  }

  useEffect(() => {
    if (fileIds.length === 0) {
      startTransition(() => {
        setSummary(null)
        setLayers(null)
      })
      return
    }

    const controller = new AbortController()
    startTransition(() => {
      setLoading(true)
      setError(null)
    })
    Promise.all(fileIds.map((fileId) => Promise.all([
      getJson<ProcessedDataSummary>(`/api/segy-files/${fileId}/processed/summary`, controller.signal),
      getJson<GeoJSONFeatureCollection>(`/api/segy-files/${fileId}/processed/lines?offset=0&limit=10000`, controller.signal),
      getJson<GeoJSONFeatureCollection>(`/api/segy-files/${fileId}/processed/shot-points?offset=0&limit=10000`, controller.signal),
      getJson<GeoJSONFeatureCollection>(`/api/segy-files/${fileId}/processed/traces?offset=0&limit=10000`, controller.signal),
    ])))
      .then((datasets) => {
        const [firstSummary] = datasets
        const [nextSummary] = firstSummary
        const aggregateSummary: ProcessedDataSummary = {
          ...nextSummary,
          id: fileIds[0],
          filename: fileIds.length === 1 ? nextSummary.filename : `${fileIds.length} surveys selected`,
          trace_count: datasets.reduce((total, [summary]) => total + summary.trace_count, 0),
          line_count: datasets.reduce((total, [summary]) => total + summary.line_count, 0),
          processed_line_count: datasets.reduce((total, [summary]) => total + summary.processed_line_count, 0),
          processed_shot_point_count: datasets.reduce((total, [summary]) => total + summary.processed_shot_point_count, 0),
          processed_trace_count: datasets.reduce((total, [summary]) => total + summary.processed_trace_count, 0),
          label: fileIds.length === 1 ? nextSummary.filename : `${fileIds.length} surveys selected`,
          color: '#e4572e',
          status: 'ready',
        }
        setSummary(aggregateSummary)
        setLayers({
          lines: { type: 'FeatureCollection', features: datasets.flatMap(([, lines]) => lines.features) },
          shotPoints: { type: 'FeatureCollection', features: datasets.flatMap(([, , shotPoints]) => shotPoints.features) },
          traces: { type: 'FeatureCollection', features: datasets.flatMap(([, , , traces]) => traces.features) },
        })
      })
      .catch((reason: unknown) => {
        if ((reason as Error).name !== 'AbortError') setError((reason as Error).message || 'Không thể tải dữ liệu đã xử lý')
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [fileIds.join(',')])

  async function deleteFiles(targetFileIds: number[]): Promise<number[]> {
    if (targetFileIds.length === 0) return []
    setDeleting(true)
    setError(null)
    try {
      const response = await fetch(`${PROCESSING_API_BASE_URL}/api/segy-files/batch-delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: targetFileIds }),
      })
      if (!response.ok) {
        throw new Error(`Backend 1 từ chối xóa dữ liệu (${response.status})`)
      }
      const result = await response.json() as BatchDeleteResponse
      setFilesRefreshToken((token) => token + 1)
      return result.deleted_ids
    } catch (reason) {
      const message = reason instanceof TypeError
        ? `Không thể kết nối Backend 1 tại ${PROCESSING_API_BASE_URL}`
        : reason instanceof Error ? reason.message : 'Không thể xóa file SEG-Y'
      setError(message)
      throw reason
    } finally {
      setDeleting(false)
    }
  }

  return { apiBaseUrl: API_BASE_URL, files, summary, layers, loading, uploading, deleting, error, uploadFiles, deleteFiles }
}
