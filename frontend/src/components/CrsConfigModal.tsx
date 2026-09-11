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
  const [targetCrsQuery, setTargetCrsQuery] = useState<string>('EPSG:4326');
  const [selectedTargetCrs, setSelectedTargetCrs] = useState<string>('EPSG:4326');
  const [isDropdownOpen, setIsDropdownOpen] = useState<boolean>(false);
  const [showTextualHeader, setShowTextualHeader] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchCrsPresets()
      .then((data) => setPresets(data))
      .catch((err) => console.warn('Không thể tải danh sách CRS presets:', err));
  }, []);

  useEffect(() => {
    if (isOpen) {
      // Default target CRS to WGS84 EPSG:4326 or whatever backend suggested
      const defaultTarget = inspection?.default_target_crs || 'EPSG:4326';
      const defaultName = inspection?.default_target_crs_name || 'WGS 84 (Địa lý)';
      setSelectedTargetCrs(defaultTarget);
      setTargetCrsQuery(`${defaultTarget} - ${defaultName}`);
      setIsDropdownOpen(false);
      setShowTextualHeader(false);
    }
  }, [isOpen, inspection]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isDropdownOpen]);

  const filteredPresets = useMemo(() => {
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

  const sourceCrsCode = inspection?.source_crs || 'EPSG:4326';
  const sourceCrsName = inspection?.source_crs_name || 'WGS 84';
  const isDetected = Boolean(inspection?.source_crs && inspection.source_crs !== 'EPSG:4326');

function cleanTargetCrsInput(input: string, presetList: CrsPreset[]): string {
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

  const handleSelectPreset = (preset: CrsPreset) => {
    setSelectedTargetCrs(preset.code);
    setTargetCrsQuery(`${preset.code} - ${preset.name}`);
    setIsDropdownOpen(false);
  };

  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setTargetCrsQuery(val);
    setSelectedTargetCrs(val.trim());
    setIsDropdownOpen(true);
  };

  const handleConfirm = () => {
    const target = cleanTargetCrsInput(selectedTargetCrs || targetCrsQuery, presets);
    onConfirm(sourceCrsCode, target);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-box modal-box--crs"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '580px', width: '92%' }}
      >
        <div className="modal-header-with-icon">
          <span className="modal-header-icon">🌐</span>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#f0f6fc' }}>
              Cấu hình Hệ Tọa Độ Dữ Liệu SEG-Y
            </h3>
            <small style={{ color: '#8b949e', fontSize: '0.8rem' }}>
              Kiểm tra hệ tọa độ gốc và chọn hệ tọa độ đích để hiển thị và lưu trữ
            </small>
          </div>
        </div>

        {inspecting ? (
          <div className="modal-inspecting-state" style={{ padding: '28px 0', textAlign: 'center' }}>
            <div className="upload-spinner" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: '#c9d1d9', margin: 0 }}>Đang trích xuất Header văn bản từ file SEG-Y...</p>
          </div>
        ) : (
          <div className="crs-modal-body" style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
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

            {/* Source CRS (Read-only) */}
            <div className="crs-input-group">
              <div className="crs-input-header">
                <label className="field-label" style={{ margin: 0 }}>
                  Hệ tọa độ gốc
                </label>
                <span
                  className={`crs-source-badge ${
                    isDetected ? 'badge-detected' : 'badge-default'
                  }`}
                >
                  {isDetected ? '✓ Trích xuất từ Header' : '⚡ Mặc định'}
                </span>
              </div>
              <div className="crs-readonly-box">
                <div className="crs-readonly-code">{sourceCrsCode}</div>
                <div className="crs-readonly-name">{sourceCrsName}</div>
              </div>
              {inspection?.trace_count ? (
                <small className="crs-detected-hint">
                  Đã kiểm tra sơ bộ tọa độ của {inspection.trace_count} trace.
                </small>
              ) : null}
            </div>

            {/* Target CRS Selection (Searchable Dropdown) */}
            <div className="crs-input-group" ref={dropdownRef}>
              <div className="crs-input-header">
                <label className="field-label" style={{ margin: 0 }}>
                  Hệ tọa độ đích muốn chuyển đổi
                </label>
                <small style={{ color: '#58a6ff', fontSize: '0.75rem' }}>
                  Gợi ý: WGS84, UTM 48N/49N, VN-2000...
                </small>
              </div>

              <div className="crs-search-wrapper" style={{ position: 'relative' }}>
                <input
                  type="text"
                  className="polygon-name-input crs-search-input"
                  style={{ margin: 0, width: '100%', paddingRight: '32px' }}
                  placeholder="Tìm kiếm mã EPSG hoặc tên hệ tọa độ..."
                  value={targetCrsQuery}
                  onChange={handleQueryChange}
                  onFocus={() => setIsDropdownOpen(true)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      setIsDropdownOpen(false);
                      handleConfirm();
                    }
                  }}
                />
                <button
                  type="button"
                  className="crs-dropdown-toggle-btn"
                  onClick={() => setIsDropdownOpen((prev) => !prev)}
                  title="Hiện danh sách gợi ý"
                >
                  ▾
                </button>

                {isDropdownOpen && (
                  <div className="crs-preset-dropdown">
                    {filteredPresets.length > 0 ? (
                      filteredPresets.map((p) => (
                        <div
                          key={p.code}
                          className={`crs-preset-item ${
                            selectedTargetCrs === p.code ? 'is-selected' : ''
                          }`}
                          onClick={() => handleSelectPreset(p)}
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

            {/* Collapsible Textual Header */}
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

        <div className="modal-actions" style={{ marginTop: '20px' }}>
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
              padding: '8px 18px',
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
