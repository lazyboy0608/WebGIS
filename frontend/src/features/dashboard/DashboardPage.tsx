import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../../App.css';
import { SeismicMap } from '../../components/SeismicMap';
import { useSeismicData } from '../../hooks/useSeismicData';
import { useAuth } from '../auth/AuthContext';

export const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  const [selectedFileIds, setSelectedFileIds] = useState<number[]>([]);
  const [showLines, setShowLines] = useState(true);
  const [showPoints, setShowPoints] = useState(true);
  const [showTraces, setShowTraces] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const [isDrawingPolygon, setIsDrawingPolygon] = useState(false);
  const [drawnPolygonRing, setDrawnPolygonRing] = useState<[number, number][] | null>(null);

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
            <button
              type="button"
              className="btn-clear-polygon"
              onClick={() => {
                setDrawnPolygonRing(null);
                setIsDrawingPolygon(false);
              }}
            >
              <span>Xóa polygon</span>
              <b>✕</b>
            </button>
          )}
          {isDrawingPolygon && (
            <small className="drawing-hint">
              Click trên bản đồ để chọn các đỉnh. Double-click hoặc click điểm đầu để hoàn thành.
            </small>
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
            onPolygonFinish={handlePolygonFinish}
          />
          {selectedFileIds.length === 0 && <div className="map-empty"><span>⌁</span><strong>Select surveys to begin</strong><small>Processed geometry will appear here</small></div>}
          {loading && <div className="loading">Loading data...</div>}
          {error && <div className="error">{error}</div>}
          <div className="map-legend">
            {drawnPolygonRing ? (
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
    </main>
  );
};
