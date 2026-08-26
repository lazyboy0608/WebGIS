import { apiClient, API_DATA_SERVING_URL, API_PROCESSING_URL } from './client';
import type {
  BatchDeleteResponse,
  FileListResponse,
  GeoJSONFeatureCollection,
  ProcessedDataSummary,
} from '../types/api';

export async function fetchSegyFiles(signal?: AbortSignal): Promise<FileListResponse> {
  return apiClient<FileListResponse>(`${API_DATA_SERVING_URL}/api/segy-files?offset=0&limit=500`, {
    signal,
  });
}

export async function fetchSegySummary(fileId: number, signal?: AbortSignal): Promise<ProcessedDataSummary> {
  return apiClient<ProcessedDataSummary>(`${API_DATA_SERVING_URL}/api/segy-files/${fileId}/processed/summary`, {
    signal,
  });
}

export async function fetchSegyLines(fileId: number, signal?: AbortSignal): Promise<GeoJSONFeatureCollection> {
  return apiClient<GeoJSONFeatureCollection>(`${API_DATA_SERVING_URL}/api/segy-files/${fileId}/processed/lines?offset=0&limit=10000`, {
    signal,
  });
}

export async function fetchSegyShotPoints(fileId: number, signal?: AbortSignal): Promise<GeoJSONFeatureCollection> {
  return apiClient<GeoJSONFeatureCollection>(`${API_DATA_SERVING_URL}/api/segy-files/${fileId}/processed/shot-points?offset=0&limit=10000`, {
    signal,
  });
}

export async function fetchSegyTraces(fileId: number, signal?: AbortSignal): Promise<GeoJSONFeatureCollection> {
  return apiClient<GeoJSONFeatureCollection>(`${API_DATA_SERVING_URL}/api/segy-files/${fileId}/processed/traces?offset=0&limit=10000`, {
    signal,
  });
}

export async function uploadSegyFiles(files: File[], sourceCrs?: string): Promise<number[]> {
  if (files.length === 0) return [];

  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  if (sourceCrs) formData.append('source_crs', sourceCrs);

  const endpoint = files.length === 1 ? '/api/segy-files/upload' : '/api/segy-files/upload/batch';
  if (files.length === 1) {
    formData.delete('files');
    formData.append('file', files[0]);
  }

  const result = await apiClient<{ segy_file_id?: number; files?: { segy_file_id: number }[] }>(
    `${API_PROCESSING_URL}${endpoint}`,
    {
      method: 'POST',
      body: formData,
    }
  );

  return result.segy_file_id !== undefined
    ? [result.segy_file_id]
    : (result.files ?? []).map((file) => file.segy_file_id);
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
