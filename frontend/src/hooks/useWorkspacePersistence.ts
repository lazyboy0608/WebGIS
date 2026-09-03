/**
 * useWorkspacePersistence
 *
 * Lưu và khôi phục workspace state của user vào localStorage.
 * Key: `webgis_workspace_<userId>` — mỗi user có namespace riêng.
 *
 * Chỉ persist những state có ý nghĩa khi restore:
 *  - selectedFileIds  : survey đang được chọn
 *  - showLines/Points/Traces : trạng thái các layer
 *  - savedPolygons    : các polygon đã đặt tên và lưu
 *  - activePolygonIds : polygon nào đang hiển thị trên bản đồ
 *
 * KHÔNG persist:
 *  - drawnPolygonRing : state tạm thời (đang vẽ dở) — không có nghĩa khi restore
 *  - isDrawingPolygon : idem
 */

import { useCallback, useEffect, useRef } from 'react';

// ─── Types ────────────────────────────────────────────────────────────────────

export type SavedPolygon = {
  id: string;
  name: string;
  ring: [number, number][];
};

export type PersistedWorkspace = {
  version: 1;
  selectedFileIds: number[];
  showLines: boolean;
  showPoints: boolean;
  showTraces: boolean;
  savedPolygons: SavedPolygon[];
  activePolygonIds: string[];
};

// ─── Defaults ─────────────────────────────────────────────────────────────────

export const DEFAULT_WORKSPACE: PersistedWorkspace = {
  version: 1,
  selectedFileIds: [],
  showLines: true,
  showPoints: true,
  showTraces: false,
  savedPolygons: [],
  activePolygonIds: [],
};

// ─── Storage helpers ──────────────────────────────────────────────────────────

function storageKey(userId: number): string {
  return `webgis_workspace_${userId}`;
}

/**
 * Đọc workspace từ localStorage. Trả về DEFAULT_WORKSPACE nếu:
 *  - Chưa có dữ liệu
 *  - JSON lỗi / schema không hợp lệ
 *  - Version không khớp (future-proof)
 */
export function loadWorkspace(userId: number): PersistedWorkspace {
  try {
    const raw = localStorage.getItem(storageKey(userId));
    if (!raw) return DEFAULT_WORKSPACE;

    const parsed = JSON.parse(raw) as Partial<PersistedWorkspace>;

    // Version guard — nếu thay đổi schema sau này, reset về default
    if (parsed.version !== 1) return DEFAULT_WORKSPACE;

    return {
      version: 1,
      selectedFileIds: Array.isArray(parsed.selectedFileIds) ? parsed.selectedFileIds : [],
      showLines: typeof parsed.showLines === 'boolean' ? parsed.showLines : true,
      showPoints: typeof parsed.showPoints === 'boolean' ? parsed.showPoints : true,
      showTraces: typeof parsed.showTraces === 'boolean' ? parsed.showTraces : false,
      savedPolygons: Array.isArray(parsed.savedPolygons) ? parsed.savedPolygons : [],
      activePolygonIds: Array.isArray(parsed.activePolygonIds) ? parsed.activePolygonIds : [],
    };
  } catch {
    // JSON.parse lỗi hoặc bất kỳ lỗi nào → graceful fallback
    return DEFAULT_WORKSPACE;
  }
}

function writeWorkspace(userId: number, workspace: PersistedWorkspace): void {
  try {
    localStorage.setItem(storageKey(userId), JSON.stringify(workspace));
  } catch {
    // localStorage có thể bị đầy hoặc bị disabled (private mode) — bỏ qua
  }
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

type SaveArgs = Omit<PersistedWorkspace, 'version'>;

/**
 * Hook quản lý persistence cho dashboard workspace.
 *
 * @param userId - ID của user đang đăng nhập (null nếu chưa auth)
 * @returns `save` function để gọi mỗi khi state thay đổi
 *
 * Cách dùng:
 * ```ts
 * const { save } = useWorkspacePersistence(user?.id ?? null);
 * useEffect(() => { save({ selectedFileIds, ... }); }, [selectedFileIds, ...]);
 * ```
 */
export function useWorkspacePersistence(userId: number | null) {
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Dọn timer khi unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current !== null) clearTimeout(debounceRef.current);
    };
  }, []);

  const save = useCallback(
    (args: SaveArgs) => {
      if (userId === null) return;

      if (debounceRef.current !== null) clearTimeout(debounceRef.current);

      debounceRef.current = setTimeout(() => {
        writeWorkspace(userId, { version: 1, ...args });
      }, 300);
    },
    [userId],
  );

  return { save };
}
