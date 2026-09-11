import { startTransition, useEffect, useState } from 'react';
import {
  deleteSegyFiles as deleteSegyFilesApi,
  exportCsvBatch,
  fetchSegyFiles,
  fetchSegyLines,
  fetchSegySummary,
  fetchSegyTaskStatus,
  inspectSegyHeader,
  subscribeSegyProgressWebSocket,
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

type TaskState = {
  taskId: string;
  status: string;
  progressPercent: number;
  message: string;
  segyFileId?: number;
  error?: string;
};

async function waitForSegyTasks(
  taskIds: string[],
  clientId: string,
  onProgress: (avgProgress: number, message: string) => void
): Promise<number[]> {
  const taskMap = new Map<string, TaskState>();
  taskIds.forEach((id) => {
    taskMap.set(id, {
      taskId: id,
      status: 'PENDING',
      progressPercent: 20,
      message: 'Đang xếp hàng xử lý...',
    });
  });

  return new Promise<number[]>((resolve, reject) => {
    let isFinished = false;

    const cleanup = () => {
      isFinished = true;
      if (pollTimer) clearInterval(pollTimer);
      if (wsUnsub) wsUnsub();
    };

    const checkCompletion = () => {
      if (isFinished) return;

      const tasks = Array.from(taskMap.values());
      const totalProgress = tasks.reduce((sum, t) => sum + t.progressPercent, 0);
      const avgProgress = Math.round(totalProgress / Math.max(tasks.length, 1));
      const latestMsg = tasks.find((t) => t.status !== 'COMPLETED')?.message || 'Hoàn tất!';

      onProgress(avgProgress, latestMsg);

      const failedTask = tasks.find((t) => t.status === 'FAILED');
      if (failedTask) {
        cleanup();
        reject(new Error(failedTask.error || `Xử lý file thất bại cho task ${failedTask.taskId}`));
        return;
      }

      const allCompleted = tasks.every((t) => t.status === 'COMPLETED');
      if (allCompleted) {
        cleanup();
        const fileIds = tasks
          .map((t) => t.segyFileId)
          .filter((id): id is number => typeof id === 'number' && id > 0);
        resolve(fileIds);
      }
    };

    const updateTaskState = (
      taskId: string,
      status: string,
      progressPercent: number,
      message: string,
      result?: any,
      error?: string
    ) => {
      const existing = taskMap.get(taskId);
      if (!existing) return;

      let fileId = existing.segyFileId;
      if (result && typeof result.segy_file_id === 'number' && result.segy_file_id > 0) {
        fileId = result.segy_file_id;
      }

      taskMap.set(taskId, {
        taskId,
        status: status || existing.status,
        progressPercent: typeof progressPercent === 'number' ? progressPercent : existing.progressPercent,
        message: message || existing.message,
        segyFileId: fileId,
        error: error || existing.error,
      });

      checkCompletion();
    };

    // 1. Subscribe to WebSocket updates
    const wsUnsub = subscribeSegyProgressWebSocket(clientId, (msg) => {
      if (msg.task_id && taskMap.has(msg.task_id)) {
        updateTaskState(
          msg.task_id,
          msg.status,
          msg.progress_percent,
          msg.message,
          msg.result,
          msg.error
        );
      }
    });

    // 2. Fallback polling every 500ms
    const pollTimer = setInterval(async () => {
      if (isFinished) return;
      for (const taskId of taskIds) {
        const current = taskMap.get(taskId);
        if (current && current.status !== 'COMPLETED' && current.status !== 'FAILED') {
          try {
            const taskData = await fetchSegyTaskStatus(taskId);
            updateTaskState(
              taskData.task_id,
              taskData.status,
              taskData.progress_percent,
              taskData.message,
              taskData.result,
              taskData.error ?? undefined
            );
          } catch {
            // ignore temporary polling errors
          }
        }
      }
    }, 500);

    checkCompletion();
  });
}

export function useSeismicData(fileIds: number[]) {
  const [files, setFiles] = useState<FileListItem[]>([]);
  const [summary, setSummary] = useState<ProcessedDataSummary | null>(null);
  const [layers, setLayers] = useState<LayerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filesRefreshToken, setFilesRefreshToken] = useState(0);

  const [progressMessage, setProgressMessage] = useState<string | null>(null);
  const [progressPercent, setProgressPercent] = useState<number>(0);

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

  async function inspectHeader(file: File) {
    return inspectSegyHeader(file);
  }

  async function uploadFiles(
    filesToUpload: File[],
    sourceCrs?: string,
    targetCrs?: string
  ): Promise<number[]> {
    if (filesToUpload.length === 0) return [];
    if (filesToUpload.some((file) => !file.name.toLowerCase().endsWith('.sgy'))) {
      throw new Error('Chỉ hỗ trợ file SEG-Y có phần mở rộng .sgy');
    }

    setUploading(true);
    setError(null);
    setProgressPercent(15);
    setProgressMessage('Truyền dữ liệu file stream tới server...');

    const clientId = `client_${Date.now()}`;

    try {
      const { taskIds, fileIds: initialFileIds } = await uploadSegyFilesApi(filesToUpload, sourceCrs, targetCrs);

      let finalFileIds: number[] = [];
      if (taskIds.length > 0) {
        finalFileIds = await waitForSegyTasks(
          taskIds,
          clientId,
          (percent, msg) => {
            setProgressPercent(percent);
            if (msg) setProgressMessage(msg);
          }
        );
      } else {
        finalFileIds = initialFileIds;
      }

      setProgressPercent(100);
      setProgressMessage('Hoàn tất xử lý!');
      setFilesRefreshToken((token) => token + 1);
      return finalFileIds;
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Không thể upload file SEG-Y';
      setError(message);
      throw reason;
    } finally {
      setTimeout(() => {
        setUploading(false);
        setProgressMessage(null);
        setProgressPercent(0);
      }, 600);
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
    ])))
      .then((datasets) => {
        const [firstDataset] = datasets;
        const [nextSummary] = firstDataset;
        const aggregateSummary: ProcessedDataSummary = {
          ...nextSummary,
          id: fileIds[0],
          filename: fileIds.length === 1 ? nextSummary.filename : `Đã chọn ${fileIds.length} khảo sát`,
          trace_count: datasets.reduce((total, [s]) => total + s.trace_count, 0),
          line_count: datasets.reduce((total, [s]) => total + s.line_count, 0),
          processed_line_count: datasets.reduce((total, [s]) => total + s.processed_line_count, 0),
          processed_shot_point_count: datasets.reduce((total, [s]) => total + s.processed_shot_point_count, 0),
          processed_trace_count: datasets.reduce((total, [s]) => total + s.processed_trace_count, 0),
          label: fileIds.length === 1 ? nextSummary.filename : `Đã chọn ${fileIds.length} khảo sát`,
          color: '#e4572e',
          status: 'ready',
        };
        setSummary(aggregateSummary);
        setLayers({
          lines: { type: 'FeatureCollection', features: datasets.flatMap(([, lines]) => (lines as GeoJSONFeatureCollection).features) },
          shotPoints: { type: 'FeatureCollection', features: [] },
          traces: { type: 'FeatureCollection', features: [] },
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

  /**
   * Export selected SEG-Y files to CSV: 1 file = 1 CSV.
   * Each CSV is uploaded to MinIO processed-segy bucket.
   * Downloads are triggered sequentially in the browser.
   */
  async function exportCsv(fileIds: number[]): Promise<void> {
    if (fileIds.length === 0) return;
    setExporting(true);
    setExportError(null);
    try {
      const results = await exportCsvBatch(fileIds);
      // Trigger sequential downloads via hidden <a> elements
      // (spacing 350 ms apart avoids popup-blocker heuristics)
      for (let i = 0; i < results.length; i++) {
        const { download_url, filename } = results[i];
        await new Promise<void>((resolve) => {
          setTimeout(() => {
            const a = document.createElement('a');
            a.href = download_url;
            a.download = filename;
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            resolve();
          }, i * 350);
        });
      }
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Không thể xuất file CSV';
      setExportError(message);
      throw reason;
    } finally {
      setExporting(false);
    }
  }

  return { apiBaseUrl: API_DATA_SERVING_URL, files, summary, layers, loading, uploading, progressMessage, progressPercent, deleting, exporting, exportError, error, inspectHeader, uploadFiles, deleteFiles, exportCsv };
}
