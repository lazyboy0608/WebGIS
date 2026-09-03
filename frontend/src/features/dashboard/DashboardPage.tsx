import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../../App.css';
import { SeismicMap } from '../../components/SeismicMap';
import { useSeismicData } from '../../hooks/useSeismicData';
import { useAuth } from '../auth/AuthContext';
import {
  loadWorkspace,
  useWorkspacePersistence,
  type SavedPolygon,
} from '../../hooks/useWorkspacePersistence';

export const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  // ── Khôi phục workspace đã lưu của user này từ localStorage ──────────────
  // useMemo đảm bảo chỉ đọc localStorage 1 lần duy nhất khi userId thay đổi
  // (không re-read mỗi render)
  const initialWorkspace = useMemo(
    () => (user ? loadWorkspace(user.id) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [user?.id],
  );

  const [selectedFileIds, setSelectedFileIds] = useState<number[]>(
    () => initialWorkspace?.selectedFileIds ?? [],
  );
  const [showLines, setShowLines] = useState<boolean>(
    () => initialWorkspace?.showLines ?? true,
  );
  const [showPoints, setShowPoints] = useState<boolean>(
    () => initialWorkspace?.showPoints ?? true,
  );
  const [showTraces, setShowTraces] = useState<boolean>(
    () => initialWorkspace?.showTraces ?? false,
  );
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const [isDrawingPolygon, setIsDrawingPolygon] = useState(false);
  // drawnPolygonRing là state tạm thời — không restore sau login
  const [drawnPolygonRing, setDrawnPolygonRing] = useState<[number, number][] | null>(null);

  // Saved polygons
  const [savedPolygons, setSavedPolygons] = useState<SavedPolygon[]>(
    () => initialWorkspace?.savedPolygons ?? [],
  );
  const [activePolygonIds, setActivePolygonIds] = useState<string[]>(
    () => initialWorkspace?.activePolygonIds ?? [],
  );
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [pendingPolygonName, setPendingPolygonName] = useState('');
  const [pendingRing, setPendingRing] = useState<[number, number][] | null>(null);

  // ── Persistence hook ──────────────────────────────────────────────────────
  const { save } = useWorkspacePersistence(user?.id ?? null);

  // Lưu workspace mỗi khi state thay đổi (debounced 300ms bên trong hook)
  useEffect(() => {
    save({ selectedFileIds, showLines, showPoints, showTraces, savedPolygons, activePolygonIds });
  }, [save, selectedFileIds, showLines, showPoints, showTraces, savedPolygons, activePolygonIds]);

  // Re-hydrate: AuthContext resolve user bất đồng bộ (cookie → /me).
  // useState lazy initializer đã chạy khi user còn null → cần apply lại
  // workspace sau khi user.id xác định lần đầu tiên.
  const hydratedRef = useRef<number | null>(null);
  useEffect(() => {
    if (!user || hydratedRef.current === user.id) return;
    hydratedRef.current = user.id;
    const ws = loadWorkspace(user.id);
    setSelectedFileIds(ws.selectedFileIds);
    setShowLines(ws.showLines);
    setShowPoints(ws.showPoints);
    setShowTraces(ws.showTraces);
    setSavedPolygons(ws.savedPolygons);
    setActivePolygonIds(ws.activePolygonIds);
  }, [user]);

  const { files, summary, layers, loading, uploading, deleting, error, uploadFiles, deleteFiles } = useSeismicData(selectedFileIds);
  const selectedFiles = files.filter((file) => selectedFileIds.includes(file.id));

  async function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? []);
    event.target.value = '';
    if (selectedFiles.length === 0) return;

    try {
      const fileIds = await uploadFiles(selectedFiles);
      if (fileIds.length > 0) setSelectedFileIds(fileIds);
    } catch {
      // The hook exposes the user-facing error state.
    }
  }

  function handleSelectAll() {
    setSelectedFileIds(files.map((file) => file.id));
  }

  function handleDeselectAll() {
    setSelectedFileIds([]);
  }

  async function handleConfirmDelete() {
    if (selectedFileIds.length === 0) return;
    try {
      await deleteFiles(selectedFileIds);
      setSelectedFileIds([]);
      setShowDeleteModal(false);
    } catch {
      // Error handled by hook
    }
  }

  function handlePolygonFinish(ring: [number, number][]) {
    setDrawnPolygonRing(ring);
    setIsDrawingPolygon(false);
  }

  function handleSavePolygonClick() {
    if (!drawnPolygonRing) return;
    setPendingRing(drawnPolygonRing);
    setPendingPolygonName('');
    setShowSaveModal(true);
  }

  function handleConfirmSavePolygon() {
    if (!pendingRing) return;
    const name = pendingPolygonName.trim() || `Polygon ${savedPolygons.length + 1}`;
    const newPolygon: SavedPolygon = {
      id: Date.now().toString(),
      name,
      ring: pendingRing,
    };
    setSavedPolygons((prev) => [...prev, newPolygon]);
    setActivePolygonIds((prev) => [...prev, newPolygon.id]);
    setShowSaveModal(false);
    setPendingRing(null);
    setPendingPolygonName('');
    // Clear the drawn polygon from the drawing tool
    setDrawnPolygonRing(null);
  }

  function handleToggleSavedPolygon(id: string) {
    setActivePolygonIds((prev) =>
      prev.includes(id) ? prev.filter((pid) => pid !== id) : [...prev, id]
    );
  }

  function handleDeleteSavedPolygon(id: string) {
    setSavedPolygons((prev) => prev.filter((p) => p.id !== id));
    setActivePolygonIds((prev) => prev.filter((pid) => pid !== id));
  }

  // Merge active saved polygon rings for map display
  const activePolygonRings = activePolygonIds
    .map((id) => savedPolygons.find((p) => p.id === id)?.ring)
    .filter((r): r is [number, number][] => Boolean(r));

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">WEBGIS / DATA SERVING</span>
          <h1>Seismic field atlas</h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {user && (
            <div className="user-profile-badge">
              <span>👤 <strong>{user.full_name}</strong></span>
              <span className={`role-tag ${user.role}`}>{user.role}</span>
              <button type="button" className="logout-btn" onClick={handleLogout}>
                Đăng xuất
              </button>
            </div>
          )}
          <span className="connection"><i /> PostGIS connected</span>
        </div>
      </header>

      <section className="workspace">
        <aside className="sidebar">
          <label className="field-label" htmlFor="file-upload">Upload SEG-Y files</label>
          <label className={`upload-button${uploading ? ' is-uploading' : ''}`} htmlFor="file-upload">
            <span>{uploading ? 'Processing...' : 'Choose .sgy files'}</span><b>+</b>
          </label>
          <input id="file-upload" className="sr-only" type="file" accept=".sgy,application/octet-stream" multiple disabled={uploading} onChange={handleFileUpload} />
          <small className="upload-hint">Files are sent to Backend 1 for processing.</small>

          <div className="surveys-header">
            <label className="field-label" htmlFor="file-select">Processed surveys</label>
            {files.length > 0 && (
              <div className="surveys-actions">
                <button type="button" className="action-link" onClick={handleSelectAll}>Tất cả</button>
                <button type="button" className="action-link" onClick={handleDeselectAll}>Bỏ chọn</button>
              </div>
            )}
          </div>
          <select id="file-select" multiple size={6} value={selectedFileIds.map(String)} onChange={(event) => setSelectedFileIds(Array.from(event.target.selectedOptions, (option) => Number(option.value)))}>
            {files.map((file) => <option key={file.id} value={file.id}>{file.label}</option>)}
          </select>
          {selectedFiles.length > 0 && (
            <>
              <div className="file-status">
                <span style={{ background: '#e4572e' }} />
                <strong>{selectedFiles.length} selected</strong>
                <small>map EPSG:4326</small>
              </div>
              <button
                type="button"
                className="delete-button"
                disabled={deleting}
                onClick={() => setShowDeleteModal(true)}
              >
                <span>{deleting ? 'Đang xóa...' : `Xóa ${selectedFiles.length} file đã chọn`}</span>
                <b>✕</b>
              </button>
            </>
          )}

          <div className="rule" />
          <p className="section-label">Spatial Filter</p>

          {/* Draw / Save / Clear controls */}
          {!drawnPolygonRing ? (
            <button
              type="button"
              className={`btn-draw-polygon${isDrawingPolygon ? ' is-active' : ''}`}
              onClick={() => setIsDrawingPolygon((prev) => !prev)}
            >
              <span>{isDrawingPolygon ? 'Hủy vẽ polygon' : 'Vẽ polygon'}</span>
              <b>⬡</b>
            </button>
          ) : (
            <div className="drawn-polygon-actions">
              <button
                type="button"
                className="btn-save-polygon"
                onClick={handleSavePolygonClick}
              >
                <span>Lưu</span>
                <b>💾</b>
              </button>
              <button
                type="button"
                className="btn-clear-polygon"
                onClick={() => {
                  setDrawnPolygonRing(null);
                  setIsDrawingPolygon(false);
                }}
              >
                <span>Xóa</span>
                <b>✕</b>
              </button>
            </div>
          )}
          {isDrawingPolygon && (
            <small className="drawing-hint">
              Click trên bản đồ để chọn các đỉnh. Double-click hoặc click điểm đầu để hoàn thành.
            </small>
          )}

          {/* Saved polygons list */}
          {savedPolygons.length > 0 && (
            <div className="saved-polygons-list">
              {savedPolygons.map((poly) => {
                const isActive = activePolygonIds.includes(poly.id);
                return (
                  <div key={poly.id} className={`saved-polygon-item${isActive ? ' is-active' : ''}`}>
                    <button
                      type="button"
                      className="saved-polygon-toggle"
                      onClick={() => handleToggleSavedPolygon(poly.id)}
                      title={isActive ? 'Ẩn polygon trên bản đồ' : 'Hiện polygon trên bản đồ'}
                    >
                      <span className="saved-polygon-dot" />
                      <span className="saved-polygon-name">{poly.name}</span>
                    </button>
                    <button
                      type="button"
                      className="saved-polygon-delete"
                      onClick={() => handleDeleteSavedPolygon(poly.id)}
                      title="Xóa polygon"
                    >
                      ✕
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          <div className="rule" />
          <p className="section-label">Map layers</p>
          <label className="toggle"><input type="checkbox" checked={showLines} onChange={(event) => setShowLines(event.target.checked)} /><span>Seismic lines</span><b>{summary?.processed_line_count ?? 0}</b></label>
          <label className="toggle"><input type="checkbox" checked={showPoints} onChange={(event) => setShowPoints(event.target.checked)} /><span>Shot points</span><b>{summary?.processed_shot_point_count ?? 0}</b></label>
          <label className="toggle"><input type="checkbox" checked={showTraces} onChange={(event) => setShowTraces(event.target.checked)} /><span>Trace positions</span><b>{summary?.processed_trace_count ?? 0}</b></label>
          <div className="sidebar-footer"><span>API endpoint</span><code>localhost:8001</code></div>
        </aside>
        <div className="map-panel">
          <SeismicMap
            data={layers}
            showLines={showLines}
            showPoints={showPoints}
            showTraces={showTraces}
            isDrawingPolygon={isDrawingPolygon}
            drawnPolygonRing={drawnPolygonRing}
            savedPolygonRings={activePolygonRings}
            onPolygonFinish={handlePolygonFinish}
          />
          {selectedFileIds.length === 0 && <div className="map-empty"><span>⌁</span><strong>Select surveys to begin</strong><small>Processed geometry will appear here</small></div>}
          {loading && <div className="loading">Loading data...</div>}
          {error && <div className="error">{error}</div>}
          <div className="map-legend">
            {(drawnPolygonRing || activePolygonRings.length > 0) ? (
              <>
                <span><i className="line-key line-inside-key" />Inside (Xanh)</span>
                <span><i className="line-key line-outside-key" />Outside (Đỏ)</span>
              </>
            ) : (
              <span><i className="line-key" />Line</span>
            )}
            <span><i className="point-key" />Shot point</span>
            <span><i className="trace-key" />Trace</span>
          </div>
        </div>
      </section>
      <footer className="summary"><div><span className="eyebrow">SELECTED DATASET</span><strong>{summary?.filename ?? 'No survey selected'}</strong></div><div className="metrics"><span><b>{summary?.processed_line_count ?? 0}</b> lines</span><span><b>{summary?.processed_shot_point_count ?? 0}</b> shot points</span><span><b>{summary?.processed_trace_count ?? 0}</b> traces</span></div></footer>

      {showDeleteModal && (
        <div className="modal-backdrop" onClick={() => !deleting && setShowDeleteModal(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Xác nhận xóa dữ liệu SEG-Y</h3>
            <p>Bạn có chắc chắn muốn xóa <strong>{selectedFiles.length}</strong> file dữ liệu thừa đã chọn? Thao tác này sẽ xóa vĩnh viễn các file và toàn bộ hình học liên quan khỏi hệ thống.</p>
            <ul className="modal-file-list">
              {selectedFiles.map((file) => (
                <li key={file.id}>• {file.filename} (#{file.id})</li>
              ))}
            </ul>
            <div className="modal-actions">
              <button type="button" className="btn-cancel" disabled={deleting} onClick={() => setShowDeleteModal(false)}>Hủy</button>
              <button type="button" className="btn-delete-confirm" disabled={deleting} onClick={handleConfirmDelete}>{deleting ? 'Đang xóa...' : 'Xóa dữ liệu'}</button>
            </div>
          </div>
        </div>
      )}

      {/* Save polygon modal */}
      {showSaveModal && (
        <div className="modal-backdrop" onClick={() => setShowSaveModal(false)}>
          <div className="modal-box modal-box--save" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-save-title">Lưu Polygon</h3>
            <p>Đặt tên cho polygon này để hiển thị trong danh sách Spatial Filter.</p>
            <input
              autoFocus
              type="text"
              className="polygon-name-input"
              placeholder="Nhập tên polygon..."
              value={pendingPolygonName}
              onChange={(e) => setPendingPolygonName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleConfirmSavePolygon(); if (e.key === 'Escape') setShowSaveModal(false); }}
            />
            <div className="modal-actions">
              <button type="button" className="btn-cancel" onClick={() => setShowSaveModal(false)}>Hủy</button>
              <button type="button" className="btn-save-confirm" onClick={handleConfirmSavePolygon}>Lưu polygon</button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
};
