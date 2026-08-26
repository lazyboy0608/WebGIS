import { startTransition, useEffect, useState } from 'react';
import {
  deleteSegyFiles as deleteSegyFilesApi,
  fetchSegyFiles,
  fetchSegyLines,
  fetchSegyShotPoints,
  fetchSegySummary,
  fetchSegyTraces,
  uploadSegyFiles as uploadSegyFilesApi,
} from '../api/seismicApi';
import { API_DATA_SERVING_URL } from '../api/client';
import type {
  FileListItem,
  GeoJSONFeatureCollection,
  LayerData,
  ProcessedDataSummary,
} from '../types/api';

function withUiFields(file: FileListItem): FileListItem {
  const hasLines = file.processed_line_count > 0;
  const hasPoints = file.processed_shot_point_count > 0 || file.processed_trace_count > 0;
  return {
    ...file,
    label: `${file.filename} (#${file.id})`,
    color: hasLines ? '#e4572e' : hasPoints ? '#1d7a8c' : '#8b949e',
    status: hasLines && hasPoints ? 'ready' : hasLines || hasPoints ? 'partial' : 'empty',
  };
}

export function useSeismicData(fileIds: number[]) {
  const [files, setFiles] = useState<FileListItem[]>([]);
  const [summary, setSummary] = useState<ProcessedDataSummary | null>(null);
  const [layers, setLayers] = useState<LayerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filesRefreshToken, setFilesRefreshToken] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    startTransition(() => setLoading(true));
    fetchSegyFiles(controller.signal)
      .then((payload) => setFiles(payload.items.map(withUiFields)))
      .catch((reason: unknown) => {
        if ((reason as Error).name !== 'AbortError') setError((reason as Error).message || 'Không thể tải danh sách SEG-Y');
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [filesRefreshToken]);

  async function uploadFiles(filesToUpload: File[], sourceCrs?: string): Promise<number[]> {
    if (filesToUpload.length === 0) return [];
    if (filesToUpload.some((file) => !file.name.toLowerCase().endsWith('.sgy'))) {
      throw new Error('Chỉ hỗ trợ file SEG-Y có phần mở rộng .sgy');
    }

    setUploading(true);
    setError(null);

    try {
      const uploadedFileIds = await uploadSegyFilesApi(filesToUpload, sourceCrs);
      setFilesRefreshToken((token) => token + 1);
      return uploadedFileIds;
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Không thể upload file SEG-Y';
      setError(message);
      throw reason;
    } finally {
      setUploading(false);
    }
  }

  useEffect(() => {
    if (fileIds.length === 0) {
      startTransition(() => {
        setSummary(null);
        setLayers(null);
      });
      return;
    }

    const controller = new AbortController();
    startTransition(() => {
      setLoading(true);
      setError(null);
    });

    Promise.all(fileIds.map((fileId) => Promise.all([
      fetchSegySummary(fileId, controller.signal),
      fetchSegyLines(fileId, controller.signal),
      fetchSegyShotPoints(fileId, controller.signal),
      fetchSegyTraces(fileId, controller.signal),
    ])))
      .then((datasets) => {
        const [firstSummary] = datasets;
        const [nextSummary] = firstSummary;
        const aggregateSummary: ProcessedDataSummary = {
          ...nextSummary,
          id: fileIds[0],
          filename: fileIds.length === 1 ? nextSummary.filename : `${fileIds.length} surveys selected`,
          trace_count: datasets.reduce((total, [s]) => total + s.trace_count, 0),
          line_count: datasets.reduce((total, [s]) => total + s.line_count, 0),
          processed_line_count: datasets.reduce((total, [s]) => total + s.processed_line_count, 0),
          processed_shot_point_count: datasets.reduce((total, [s]) => total + s.processed_shot_point_count, 0),
          processed_trace_count: datasets.reduce((total, [s]) => total + s.processed_trace_count, 0),
          label: fileIds.length === 1 ? nextSummary.filename : `${fileIds.length} surveys selected`,
          color: '#e4572e',
          status: 'ready',
        };
        setSummary(aggregateSummary);
        setLayers({
          lines: { type: 'FeatureCollection', features: datasets.flatMap(([, lines]) => (lines as GeoJSONFeatureCollection).features) },
          shotPoints: { type: 'FeatureCollection', features: datasets.flatMap(([, , shotPoints]) => (shotPoints as GeoJSONFeatureCollection).features) },
          traces: { type: 'FeatureCollection', features: datasets.flatMap(([, , , traces]) => (traces as GeoJSONFeatureCollection).features) },
        });
      })
      .catch((reason: unknown) => {
        if ((reason as Error).name !== 'AbortError') setError((reason as Error).message || 'Không thể tải dữ liệu đã xử lý');
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [fileIds.join(',')]);

  async function deleteFiles(targetFileIds: number[]): Promise<number[]> {
    if (targetFileIds.length === 0) return [];
    setDeleting(true);
    setError(null);
    try {
      const deletedIds = await deleteSegyFilesApi(targetFileIds);
      setFilesRefreshToken((token) => token + 1);
      return deletedIds;
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Không thể xóa file SEG-Y';
      setError(message);
      throw reason;
    } finally {
      setDeleting(false);
    }
  }

  return { apiBaseUrl: API_DATA_SERVING_URL, files, summary, layers, loading, uploading, deleting, error, uploadFiles, deleteFiles };
}
