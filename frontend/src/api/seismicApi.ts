import { apiClient, API_DATA_SERVING_URL, API_PROCESSING_URL } from './client';
import type {
  BatchDeleteResponse,
  CrsPreset,
  FileListResponse,
  GeoJSONFeatureCollection,
  ProcessedDataSummary,
  SegyHeaderInspectionResult,
  SegyTaskStatusResponse,
} from '../types/api';

export type ExportCsvResult = {
  segy_file_id: number;
  filename: string;
  object_name: string;
  bucket: string;
  size_bytes: number;
  record_count: number;
  download_url: string;
};

type BatchExportCsvResponse = {
  results: ExportCsvResult[];
  total: number;
};

export async function fetchSegyFiles(signal?: AbortSignal): Promise<FileListResponse> {
  return apiClient<FileListResponse>(`${API_DATA_SERVING_URL}/api/segy-files?offset=0&limit=500`, {
    signal,
  });
}

export async function fetchSegySummary(
  fileId: number,
  signal?: AbortSignal
): Promise<ProcessedDataSummary> {
  return apiClient<ProcessedDataSummary>(
    `${API_DATA_SERVING_URL}/api/segy-files/${fileId}/processed/summary`,
    { signal }
  );
}

export async function fetchSegyLines(
  fileId: number,
  signal?: AbortSignal
): Promise<GeoJSONFeatureCollection> {
  return apiClient<GeoJSONFeatureCollection>(
    `${API_DATA_SERVING_URL}/api/segy-files/${fileId}/processed/lines?limit=10000`,
    { signal }
  );
}

export async function fetchSegyShotPoints(
  fileId: number,
  signal?: AbortSignal
): Promise<GeoJSONFeatureCollection> {
  return apiClient<GeoJSONFeatureCollection>(
    `${API_DATA_SERVING_URL}/api/segy-files/${fileId}/processed/shot-points?limit=10000`,
    { signal }
  );
}

export async function fetchSegyTraces(
  fileId: number,
  signal?: AbortSignal
): Promise<GeoJSONFeatureCollection> {
  return apiClient<GeoJSONFeatureCollection>(
    `${API_DATA_SERVING_URL}/api/segy-files/${fileId}/processed/traces?limit=10000`,
    { signal }
  );
}

export type SegyUploadResult = {
  taskIds: string[];
  fileIds: number[];
};

export async function fetchSegyTaskStatus(taskId: string): Promise<SegyTaskStatusResponse> {
  return apiClient<SegyTaskStatusResponse>(`${API_PROCESSING_URL}/api/segy-files/tasks/${taskId}`);
}

export async function inspectSegyHeader(file: File): Promise<SegyHeaderInspectionResult> {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient<SegyHeaderInspectionResult>(`${API_PROCESSING_URL}/api/segy-files/inspect-header`, {
    method: 'POST',
    body: formData,
  });
}

export async function fetchCrsPresets(): Promise<CrsPreset[]> {
  return apiClient<CrsPreset[]>(`${API_PROCESSING_URL}/api/segy-files/crs-presets`);
}

export async function uploadSegyFiles(
  files: File[],
  sourceCrs?: string,
  targetCrs?: string
): Promise<SegyUploadResult> {
  if (files.length === 0) return { taskIds: [], fileIds: [] };

  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  if (sourceCrs) formData.append('source_crs', sourceCrs);
  if (targetCrs) formData.append('target_crs', targetCrs);

  const endpoint = files.length === 1 ? '/api/segy-files/upload' : '/api/segy-files/upload/batch';
  if (files.length === 1) {
    formData.delete('files');
    formData.append('file', files[0]);
  }

  const result = await apiClient<{
    segy_file_id?: number;
    task_id?: string;
    files?: { segy_file_id?: number; task_id?: string }[];
  }>(`${API_PROCESSING_URL}${endpoint}`, {
    method: 'POST',
    body: formData,
  });

  const rawList = result.files ?? (result.segy_file_id !== undefined || result.task_id !== undefined ? [result] : []);
  const taskIds = rawList.map((item) => item.task_id).filter((id): id is string => Boolean(id));
  const fileIds = rawList
    .map((item) => item.segy_file_id)
    .filter((id): id is number => typeof id === 'number' && id > 0);

  return { taskIds, fileIds };
}

export async function deleteSegyFiles(targetFileIds: number[]): Promise<number[]> {
  if (targetFileIds.length === 0) return [];

  const result = await apiClient<BatchDeleteResponse>(
    `${API_PROCESSING_URL}/api/segy-files/batch-delete`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: targetFileIds }),
    }
  );

  return result.deleted_ids;
}

export async function exportCsvBatch(fileIds: number[]): Promise<ExportCsvResult[]> {
  if (fileIds.length === 0) return [];

  const result = await apiClient<BatchExportCsvResponse>(
    `${API_DATA_SERVING_URL}/api/segy-files/export/csv/batch`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: fileIds }),
    }
  );

  return result.results;
}

export type ExportSegyResult = {
  segy_file_id: number;
  line_id: string;
  filename: string;
  object_name: string;
  bucket: string;
  size_bytes: number;
  trace_count: number;
  download_url: string;
};

type BatchExportSegyResponse = {
  results: ExportSegyResult[];
  total: number;
};

export async function exportSegySpatialFilter(
  polygonRing: [number, number][],
  polygonName: string = 'spatial_filter',
  fileIds?: number[],
  targetCrs?: string
): Promise<ExportSegyResult[]> {
  const result = await apiClient<BatchExportSegyResponse>(
    `${API_DATA_SERVING_URL}/api/segy-files/export/segy/spatial-filter`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        polygon_ring: polygonRing,
        polygon_name: polygonName,
        file_ids: fileIds && fileIds.length > 0 ? fileIds : undefined,
        target_crs: targetCrs,
      }),
    }
  );

  return result.results;
}


export type SegyProgressMessage = {
  type: string
  task_id: string
  filename: string
  status: string
  progress_percent: number
  message: string
  result?: any
  error?: string
  timestamp?: string
}

export function subscribeSegyProgressWebSocket(
  clientId: string,
  onMessage: (msg: SegyProgressMessage) => void
): () => void {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsHost = window.location.host
  const wsUrl = `${wsProtocol}//${wsHost}/api/segy-files/ws/progress/${clientId}`

  let ws: WebSocket | null = null
  let isClosed = false

  try {
    ws = new WebSocket(wsUrl)
    ws.onmessage = (event) => {
      if (isClosed) return
      try {
        const data = JSON.parse(event.data) as SegyProgressMessage
        onMessage(data)
      } catch {
        // ignore parse error
      }
    }
  } catch {
    // ignore websocket init error
  }

  return () => {
    isClosed = true
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      ws.close()
    }
  }
}

export function getSegyMvtTileUrlTemplate(fileIds?: number[]): string {
  const query = fileIds && fileIds.length > 0 ? `?file_ids=${fileIds.join(',')}` : ''
  return `${API_DATA_SERVING_URL}/api/segy-files/mvt/{z}/{x}/{y}.pbf${query}`
}

export type BatchSpatialFilterClipResponse = {
  inside: GeoJSONFeatureCollection
  outside: GeoJSONFeatureCollection
}

export async function clipSegyLinesBatch(
  fileIds: number[],
  polygonRings: [number, number][][]
): Promise<BatchSpatialFilterClipResponse> {
  if (fileIds.length === 0 || polygonRings.length === 0) {
    return {
      inside: { type: 'FeatureCollection', features: [] },
      outside: { type: 'FeatureCollection', features: [] },
    }
  }

  return apiClient<BatchSpatialFilterClipResponse>(
    `${API_DATA_SERVING_URL}/api/segy-files/spatial-filter/clip`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_ids: fileIds,
        polygon_rings: polygonRings,
      }),
    }
  )
}



