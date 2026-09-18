import React, { useEffect, useMemo, useRef, useState } from 'react';
import { fetchCrsPresets } from '../api/seismicApi';
import type { CrsPreset, SegyHeaderInspectionResult } from '../types/api';

interface CrsConfigModalProps {
  isOpen: boolean;
  files: File[];
  inspection: SegyHeaderInspectionResult | null;
  inspecting: boolean;
  onClose: () => void;
  onConfirm: (sourceCrs: string, targetCrs: string) => void;
}

export const CrsConfigModal: React.FC<CrsConfigModalProps> = ({
  isOpen,
  files,
  inspection,
  inspecting,
  onClose,
  onConfirm,
}) => {
  const [presets, setPresets] = useState<CrsPreset[]>([]);

  // Source CRS states (Editable + Searchable dropdown)
  const [sourceCrsQuery, setSourceCrsQuery] = useState<string>('EPSG:32648');
  const [selectedSourceCrs, setSelectedSourceCrs] = useState<string>('EPSG:32648');
  const [isSourceDropdownOpen, setIsSourceDropdownOpen] = useState<boolean>(false);
  const sourceDropdownRef = useRef<HTMLDivElement>(null);

  // Target CRS states
  const [targetCrsQuery, setTargetCrsQuery] = useState<string>('EPSG:4326');
  const [selectedTargetCrs, setSelectedTargetCrs] = useState<string>('EPSG:4326');
  const [isTargetDropdownOpen, setIsTargetDropdownOpen] = useState<boolean>(false);
  const targetDropdownRef = useRef<HTMLDivElement>(null);

  // Collapsible panels
  const [showTextualHeader, setShowTextualHeader] = useState<boolean>(false);
  const [showTracePreview, setShowTracePreview] = useState<boolean>(true);

  useEffect(() => {
    fetchCrsPresets()
      .then((data) => setPresets(data))
      .catch((err) => console.warn('Không thể tải danh sách CRS presets:', err));
  }, []);

  useEffect(() => {
    if (isOpen) {
      // Initialize Source CRS with inspection result
      const detectedSource = inspection?.source_crs || 'EPSG:32648';
      const detectedSourceName = inspection?.source_crs_name || 'WGS 84 / UTM zone 48N';
      setSelectedSourceCrs(detectedSource);
      setSourceCrsQuery(`${detectedSource} - ${detectedSourceName}`);
      setIsSourceDropdownOpen(false);

      // Initialize Target CRS with WGS84 EPSG:4326
      const defaultTarget = inspection?.default_target_crs || 'EPSG:4326';
      const defaultTargetName = inspection?.default_target_crs_name || 'WGS 84 (Kinh độ / Vĩ độ)';
      setSelectedTargetCrs(defaultTarget);
      setTargetCrsQuery(`${defaultTarget} - ${defaultTargetName}`);
      setIsTargetDropdownOpen(false);

      setShowTextualHeader(false);
      setShowTracePreview(true);
    }
  }, [isOpen, inspection]);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (sourceDropdownRef.current && !sourceDropdownRef.current.contains(e.target as Node)) {
        setIsSourceDropdownOpen(false);
      }
      if (targetDropdownRef.current && !targetDropdownRef.current.contains(e.target as Node)) {
        setIsTargetDropdownOpen(false);
      }
    };
    if (isSourceDropdownOpen || isTargetDropdownOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isSourceDropdownOpen, isTargetDropdownOpen]);

  const filteredSourcePresets = useMemo(() => {
    const q = sourceCrsQuery.toLowerCase().trim();
    if (!q) return presets;
    return presets.filter(
      (p) =>
        p.code.toLowerCase().includes(q) ||
        p.name.toLowerCase().includes(q) ||
        (p.category && p.category.toLowerCase().includes(q)) ||
        (p.description && p.description.toLowerCase().includes(q))
    );
  }, [presets, sourceCrsQuery]);

  const filteredTargetPresets = useMemo(() => {
    const q = targetCrsQuery.toLowerCase().trim();
    if (!q) return presets;
    return presets.filter(
      (p) =>
        p.code.toLowerCase().includes(q) ||
        p.name.toLowerCase().includes(q) ||
        (p.category && p.category.toLowerCase().includes(q)) ||
        (p.description && p.description.toLowerCase().includes(q))
    );
  }, [presets, targetCrsQuery]);

  if (!isOpen) return null;

  const detectedSourceCode = inspection?.source_crs || 'EPSG:32648';
  const isSourceCustomized = Boolean(selectedSourceCrs && selectedSourceCrs !== detectedSourceCode);

  function cleanCrsInput(input: string, presetList: CrsPreset[]): string {
    if (!input) return 'EPSG:4326';
    const trimmed = input.trim();

    // 1. Direct match with preset code or full label
    const exactPreset = presetList.find(
      (p) =>
        p.code.toLowerCase() === trimmed.toLowerCase() ||
        `${p.code} - ${p.name}`.toLowerCase() === trimmed.toLowerCase()
    );
    if (exactPreset) return exactPreset.code;

    // 2. Extract EPSG:XXXX if present
    const epsgMatch = trimmed.match(/EPSG:\d+/i);
    if (epsgMatch) return epsgMatch[0].toUpperCase();

    // 3. Digits only
    if (/^\d+$/.test(trimmed)) return `EPSG:${trimmed}`;

    // 4. Fuzzy match against preset name or category
    const fuzzy = presetList.find(
      (p) =>
        p.name.toLowerCase().includes(trimmed.toLowerCase()) ||
        (p.category && p.category.toLowerCase().includes(trimmed.toLowerCase()))
    );
    if (fuzzy) return fuzzy.code;

    return trimmed;
  }

  const handleSelectSourcePreset = (preset: CrsPreset) => {
    setSelectedSourceCrs(preset.code);
    setSourceCrsQuery(`${preset.code} - ${preset.name}`);
    setIsSourceDropdownOpen(false);
  };

  const handleSelectTargetPreset = (preset: CrsPreset) => {
    setSelectedTargetCrs(preset.code);
    setTargetCrsQuery(`${preset.code} - ${preset.name}`);
    setIsTargetDropdownOpen(false);
  };

  const handleConfirm = () => {
    const source = cleanCrsInput(selectedSourceCrs || sourceCrsQuery, presets);
    const target = cleanCrsInput(selectedTargetCrs || targetCrsQuery, presets);
    onConfirm(source, target);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-box modal-box--crs modal-box--crs-wide"
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: '880px',
          width: '95%',
          maxHeight: '88vh',
          overflowY: 'scroll',
          padding: '24px',
          position: 'relative',
        }}
      >
        <div className="modal-header-with-icon">
          <span className="modal-header-icon">🌐</span>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#f0f6fc', display: 'flex', alignItems: 'center', gap: '8px' }}>
              Cấu hình Hệ Tọa Độ & Kiểm Tra File SEG-Y
            </h3>
            <small style={{ color: '#8b949e', fontSize: '0.8125rem' }}>
              Kiểm tra thông số Header, tỷ lệ tọa độ (SAC / SAED) và chọn hệ tọa độ đích
            </small>
          </div>
        </div>

        {inspecting ? (
          <div className="modal-inspecting-state" style={{ padding: '36px 0', textAlign: 'center' }}>
            <div className="upload-spinner" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: '#c9d1d9', margin: 0, fontWeight: 500 }}>
              Đang phân tích Header và trích xuất dữ liệu trace từ file SEG-Y...
            </p>
          </div>
        ) : (
          <div
            className="crs-modal-body"
            style={{
              marginTop: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            {/* File info banner */}
            <div className="crs-info-row file-banner">
              <span className="crs-label">File đã chọn:</span>
              <div className="crs-file-tags">
                {files.map((f, idx) => (
                  <span key={idx} className="crs-file-tag">
                    📄 <strong>{f.name}</strong> ({(f.size / (1024 * 1024)).toFixed(2)} MB)
                  </span>
                ))}
              </div>
            </div>

            {/* Parsed Header Summary Cards (Ảnh 1) */}
            {inspection?.header_details && (
              <div className="crs-header-details-container">
                <span className="crs-label" style={{ marginBottom: '6px', display: 'block' }}>
                  Thông tin trích xuất từ Header văn bản (Survey & Navigation):
                </span>
                <div className="crs-header-details-grid">
                  {inspection.header_details.survey && (
                    <div className="crs-detail-card highlight-card">
                      <span className="crs-detail-title">Khảo sát / Lô (Survey):</span>
                      <span className="crs-detail-val highlight">{inspection.header_details.survey}</span>
                    </div>
                  )}
                  {inspection.header_details.line_id && (
                    <div className="crs-detail-card">
                      <span className="crs-detail-title">Tuyến (Line ID):</span>
                      <span className="crs-detail-val">{inspection.header_details.line_id}</span>
                    </div>
                  )}
                  {inspection.header_details.datum && (
                    <div className="crs-detail-card">
                      <span className="crs-detail-title">Hệ quy chiếu (Datum):</span>
                      <span className="crs-detail-val">{inspection.header_details.datum}</span>
                    </div>
                  )}
                  {inspection.header_details.projection && (
                    <div className="crs-detail-card">
                      <span className="crs-detail-title">Phép chiếu (Projection):</span>
                      <span className="crs-detail-val">{inspection.header_details.projection}</span>
                    </div>
                  )}
                  {inspection.header_details.zone && (
                    <div className="crs-detail-card">
                      <span className="crs-detail-title">Múi chiếu (Zone):</span>
                      <span className="crs-detail-val">Zone {inspection.header_details.zone}</span>
                    </div>
                  )}
                  {inspection.header_details.central_meridian && (
                    <div className="crs-detail-card">
                      <span className="crs-detail-title">Kinh tuyến trục (CM):</span>
                      <span className="crs-detail-val">{inspection.header_details.central_meridian}</span>
                    </div>
                  )}
                  {inspection.header_details.scale_factor !== undefined && inspection.header_details.scale_factor !== null && (
                    <div className="crs-detail-card">
                      <span className="crs-detail-title">Scale Factor (k0):</span>
                      <span className="crs-detail-val">{inspection.header_details.scale_factor}</span>
                    </div>
                  )}
                  {inspection.header_details.false_easting !== undefined && inspection.header_details.false_easting !== null && (
                    <div className="crs-detail-card">
                      <span className="crs-detail-title">False Easting (m):</span>
                      <span className="crs-detail-val">{inspection.header_details.false_easting.toLocaleString()}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Source CRS Selection (Click / Search / Edit) (Ảnh 3) */}
            <div className="crs-input-group" ref={sourceDropdownRef}>
              <div className="crs-input-header">
                <label className="field-label" style={{ margin: 0 }}>
                  Hệ tọa độ gốc (Source CRS) — Có thể chọn hoặc chỉnh sửa:
                </label>
                <span
                  className={`crs-source-badge ${
                    isSourceCustomized ? 'badge-custom' : 'badge-detected'
                  }`}
                  title={isSourceCustomized ? 'Bạn đã chỉnh sửa so với giá trị đọc từ file' : 'Hệ thống tự động suy luận từ Header'}
                >
                  {isSourceCustomized ? '✏️ Người dùng tùy chỉnh' : '✓ Trích xuất từ Header'}
                </span>
              </div>

              <div className="crs-search-wrapper" style={{ position: 'relative' }}>
                <input
                  type="text"
                  className="polygon-name-input crs-search-input"
                  style={{ margin: 0, width: '100%', paddingRight: '32px' }}
                  placeholder="Click hoặc gõ để chọn/sửa hệ tọa độ gốc (ví dụ: EPSG:32648, UTM 48N...)"
                  value={sourceCrsQuery}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSourceCrsQuery(val);
                    setSelectedSourceCrs(val.trim());
                    setIsSourceDropdownOpen(true);
                  }}
                  onFocus={() => setIsSourceDropdownOpen(true)}
                />
                <button
                  type="button"
                  className="crs-dropdown-toggle-btn"
                  onClick={() => setIsSourceDropdownOpen((prev) => !prev)}
                  title="Hiện danh sách gợi ý hệ tọa độ gốc"
                >
                  ▾
                </button>

                {isSourceDropdownOpen && (
                  <div className="crs-preset-dropdown">
                    {filteredSourcePresets.length > 0 ? (
                      filteredSourcePresets.map((p) => (
                        <div
                          key={p.code}
                          className={`crs-preset-item ${
                            selectedSourceCrs === p.code ? 'is-selected' : ''
                          }`}
                          onClick={() => handleSelectSourcePreset(p)}
                        >
                          <div className="crs-preset-top">
                            <span className="crs-preset-code">{p.code}</span>
                            {p.category && <span className="crs-preset-category">{p.category}</span>}
                          </div>
                          <div className="crs-preset-name">{p.name}</div>
                          {p.description && (
                            <div className="crs-preset-desc">{p.description}</div>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="crs-preset-empty">
                        <small>Bạn có thể sử dụng trực tiếp: <strong>{sourceCrsQuery}</strong></small>
                      </div>
                    )}
                  </div>
                )}
              </div>
              <small className="crs-detected-hint">
                💡 Bạn có thể kiểm tra tọa độ mẫu bên dưới và đổi múi chiếu (UTM 48N vs UTM 49N) nếu cần thiết.
              </small>
            </div>

            {/* Target CRS Selection (Searchable Dropdown) */}
            <div className="crs-input-group" ref={targetDropdownRef}>
              <div className="crs-input-header">
                <label className="field-label" style={{ margin: 0 }}>
                  Hệ tọa độ đích muốn chuyển đổi (Target CRS):
                </label>
                <small style={{ color: '#58a6ff', fontSize: '0.75rem' }}>
                  Khuyên dùng WGS 84 (EPSG:4326) để hiển thị đồng bộ lên bản đồ WebGIS
                </small>
              </div>

              <div className="crs-search-wrapper" style={{ position: 'relative' }}>
                <input
                  type="text"
                  className="polygon-name-input crs-search-input"
                  style={{ margin: 0, width: '100%', paddingRight: '32px' }}
                  placeholder="Tìm kiếm mã EPSG hoặc tên hệ tọa độ..."
                  value={targetCrsQuery}
                  onChange={(e) => {
                    const val = e.target.value;
                    setTargetCrsQuery(val);
                    setSelectedTargetCrs(val.trim());
                    setIsTargetDropdownOpen(true);
                  }}
                  onFocus={() => setIsTargetDropdownOpen(true)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      setIsTargetDropdownOpen(false);
                      handleConfirm();
                    }
                  }}
                />
                <button
                  type="button"
                  className="crs-dropdown-toggle-btn"
                  onClick={() => setIsTargetDropdownOpen((prev) => !prev)}
                  title="Hiện danh sách gợi ý"
                >
                  ▾
                </button>

                {isTargetDropdownOpen && (
                  <div className="crs-preset-dropdown">
                    {filteredTargetPresets.length > 0 ? (
                      filteredTargetPresets.map((p) => (
                        <div
                          key={p.code}
                          className={`crs-preset-item ${
                            selectedTargetCrs === p.code ? 'is-selected' : ''
                          }`}
                          onClick={() => handleSelectTargetPreset(p)}
                        >
                          <div className="crs-preset-top">
                            <span className="crs-preset-code">{p.code}</span>
                            {p.category && <span className="crs-preset-category">{p.category}</span>}
                          </div>
                          <div className="crs-preset-name">{p.name}</div>
                          {p.description && (
                            <div className="crs-preset-desc">{p.description}</div>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="crs-preset-empty">
                        <small>Không tìm thấy mẫu phù hợp. Bạn có thể sử dụng trực tiếp: <strong>{targetCrsQuery}</strong></small>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Trace Inspection Table (Ảnh 2 & Ảnh 3) */}
            {inspection?.sample_traces && inspection.sample_traces.length > 0 && (
              <div className="crs-trace-preview-section">
                <button
                  type="button"
                  className="crs-header-toggle-btn"
                  onClick={() => setShowTracePreview((prev) => !prev)}
                >
                  <span>
                    {showTracePreview
                      ? '▼ Ẩn bảng kiểm tra trace'
                      : `▶ Kiểm tra ${inspection.sample_traces.length} trace đầu của file (Kiểm tra SAC, SAED & Tọa độ)`}
                  </span>
                </button>

                {showTracePreview && (
                  <div className="crs-trace-table-container">
                    <table className="crs-trace-table">
                      <thead>
                        <tr>
                          <th style={{ minWidth: '70px', width: '70px' }}>Trace</th>
                          <th style={{ minWidth: '130px', width: '130px' }}>SAC (Bytes 71-72)</th>
                          <th style={{ minWidth: '130px', width: '130px' }}>SAED (Bytes 69-70)</th>
                          <th style={{ minWidth: '120px', width: '120px' }}>Scaler áp dụng</th>
                          <th style={{ minWidth: '135px', width: '135px' }}>Toạ độ X gốc</th>
                          <th style={{ minWidth: '135px', width: '135px' }}>Toạ độ Y gốc</th>
                          <th style={{ minWidth: '160px', width: '160px' }}>Toạ độ X sau Scaler (m)</th>
                          <th style={{ minWidth: '160px', width: '160px' }}>Toạ độ Y sau Scaler (m)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {inspection.sample_traces.map((t) => {
                          const hasSac = t.sac !== null && t.sac !== undefined && t.sac !== 0 && t.sac !== 1;
                          const hasSaed = t.saed !== null && t.saed !== undefined && t.saed !== 0 && t.saed !== 1;
                          const scalerLabel =
                            t.effective_scalar < 0
                              ? `1/${Math.abs(t.effective_scalar)}`
                              : t.effective_scalar > 1
                              ? `x${t.effective_scalar}`
                              : '1 (Không đổi)';

                          return (
                            <tr key={t.trace_index}>
                              <td className="center-cell">{t.trace_sequence_line ?? t.trace_index}</td>
                              <td className={`center-cell ${hasSac ? 'badge-sac' : 'dim-cell'}`}>
                                {t.sac ?? 0}
                              </td>
                              <td className={`center-cell ${hasSaed ? 'badge-saed' : 'dim-cell'}`}>
                                {t.saed ?? 0}
                              </td>
                              <td className="center-cell bold-cell">{scalerLabel}</td>
                              <td className="right-cell mono-font">
                                {t.source_x ? t.source_x.toLocaleString() : (t.cdp_x ? t.cdp_x.toLocaleString() : '-')}
                              </td>
                              <td className="right-cell mono-font">
                                {t.source_y ? t.source_y.toLocaleString() : (t.cdp_y ? t.cdp_y.toLocaleString() : '-')}
                              </td>
                              <td className="right-cell mono-font green-cell">
                                {t.scaled_x ? t.scaled_x.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}
                              </td>
                              <td className="right-cell mono-font green-cell">
                                {t.scaled_y ? t.scaled_y.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                    <small className="crs-table-footnote">
                      * Hệ thống tự động ưu tiên SAC (Scaler to all coordinates). Nếu SAC không hợp lệ (bằng 0 hoặc 1), hệ thống sẽ tự động fallback sang SAED (Scaler to all elevations).
                    </small>
                  </div>
                )}
              </div>
            )}

            {/* Collapsible Textual Header (3200 bytes) */}
            {inspection?.textual_header_preview && (
              <div className="crs-header-collapsible">
                <button
                  type="button"
                  className="crs-header-toggle-btn"
                  onClick={() => setShowTextualHeader((prev) => !prev)}
                >
                  <span>{showTextualHeader ? '▼ Ẩn Header văn bản gốc' : '▶ Xem trích đoạn Header văn bản gốc (3200 bytes)'}</span>
                </button>
                {showTextualHeader && (
                  <pre className="crs-header-content">
                    {inspection.textual_header_preview}
                  </pre>
                )}
              </div>
            )}
          </div>
        )}

        <div
          className="modal-actions"
          style={{
            marginTop: '20px',
            paddingTop: '16px',
            borderTop: '1px solid #21262d',
            position: 'sticky',
            bottom: '-24px',
            background: '#161b22',
            zIndex: 20,
            paddingBottom: '8px',
          }}
        >
          <button
            type="button"
            className="btn-cancel"
            disabled={inspecting}
            onClick={onClose}
          >
            Hủy bỏ
          </button>
          <button
            type="button"
            className="btn-save-confirm"
            style={{
              background: '#238636',
              borderColor: '#2ea043',
              padding: '8px 20px',
              fontWeight: 600,
            }}
            disabled={inspecting}
            onClick={handleConfirm}
          >
            Tải lên & Chuyển đổi
          </button>
        </div>
      </div>
    </div>
  );
};
