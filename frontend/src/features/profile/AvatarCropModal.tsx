import React, { useState, useRef, useEffect, useCallback } from 'react';

interface AvatarCropModalProps {
  imageSrc: string;
  onCropComplete: (croppedFile: File, croppedPreviewUrl: string) => void;
  onClose: () => void;
}

const CANVAS_SIZE = 340;
const CROP_RADIUS = 130; // Đường kính khung tròn 260px
const CENTER = CANVAS_SIZE / 2; // 170px
const EXPORT_SIZE = 512; // Kích thước ảnh avatar xuất ra chuẩn nét (512x512)

export const AvatarCropModal: React.FC<AvatarCropModalProps> = ({
  imageSrc,
  onCropComplete,
  onClose,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);

  const [zoom, setZoom] = useState<number>(1.0);
  const [rotation, setRotation] = useState<number>(0);
  const [offset, setOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [imageLoaded, setImageLoaded] = useState<boolean>(false);

  // Tính toán giới hạn kéo (Clamping) để ảnh luôn phủ kín vòng tròn
  const getClampedOffset = useCallback(
    (
      rawOffset: { x: number; y: number },
      currentZoom: number,
      currentRotation: number,
      img: HTMLImageElement
    ) => {
      const isRotated = currentRotation === 90 || currentRotation === 270;
      const effectiveW = isRotated ? img.height : img.width;
      const effectiveH = isRotated ? img.width : img.height;

      const baseScale = Math.max((CROP_RADIUS * 2) / effectiveW, (CROP_RADIUS * 2) / effectiveH);
      const totalScale = baseScale * currentZoom;

      const renderedW = effectiveW * totalScale;
      const renderedH = effectiveH * totalScale;

      const maxOffsetX = Math.max(0, (renderedW - CROP_RADIUS * 2) / 2);
      const maxOffsetY = Math.max(0, (renderedH - CROP_RADIUS * 2) / 2);

      return {
        x: Math.min(maxOffsetX, Math.max(-maxOffsetX, rawOffset.x)),
        y: Math.min(maxOffsetY, Math.max(-maxOffsetY, rawOffset.y)),
      };
    },
    []
  );

  // Khởi tạo và tải ảnh
  useEffect(() => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      imageRef.current = img;
      setImageLoaded(true);
      setOffset({ x: 0, y: 0 });
      setZoom(1.0);
      setRotation(0);
    };
    img.src = imageSrc;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [imageSrc, onClose]);

  // Vẽ ảnh và khung cắt tròn lên Canvas
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img || !imageLoaded) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

    const isRotated = rotation === 90 || rotation === 270;
    const effectiveW = isRotated ? img.height : img.width;
    const effectiveH = isRotated ? img.width : img.height;

    const baseScale = Math.max((CROP_RADIUS * 2) / effectiveW, (CROP_RADIUS * 2) / effectiveH);
    const totalScale = baseScale * zoom;

    // 1. Vẽ ảnh sau khi dịch chuyển, xoay và phóng to
    ctx.save();
    ctx.translate(CENTER + offset.x, CENTER + offset.y);
    ctx.rotate((rotation * Math.PI) / 180);
    ctx.scale(totalScale, totalScale);
    ctx.drawImage(img, -img.width / 2, -img.height / 2);
    ctx.restore();

    // 2. Vẽ lớp phủ tối làm mờ vùng bên ngoài vòng tròn (Mask)
    ctx.save();
    ctx.fillStyle = 'rgba(15, 23, 42, 0.6)';
    ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

    // Đục lỗ tròn trong suốt ở giữa
    ctx.globalCompositeOperation = 'destination-out';
    ctx.beginPath();
    ctx.arc(CENTER, CENTER, CROP_RADIUS, 0, Math.PI * 2);
    ctx.fill();

    // Khôi phục chế độ vẽ thông thường
    ctx.globalCompositeOperation = 'source-over';

    // Viền chính của vòng tròn cắt
    ctx.strokeStyle = '#1d7a8c';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(CENTER, CENTER, CROP_RADIUS, 0, Math.PI * 2);
    ctx.stroke();

    // Vòng nét đứt mảnh trợ thị căn tâm
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.arc(CENTER, CENTER, CROP_RADIUS - 1, 0, Math.PI * 2);
    ctx.stroke();

    ctx.restore();
  }, [imageLoaded, zoom, rotation, offset]);

  useEffect(() => {
    draw();
  }, [draw]);

  // Xử lý kéo thả bằng chuột
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging || !imageRef.current) return;
    const rawOffset = { x: e.clientX - dragStart.x, y: e.clientY - dragStart.y };
    const clamped = getClampedOffset(rawOffset, zoom, rotation, imageRef.current);
    setOffset(clamped);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Xử lý kéo thả trên màn hình cảm ứng
  const handleTouchStart = (e: React.TouchEvent<HTMLCanvasElement>) => {
    if (e.touches.length === 1) {
      setIsDragging(true);
      setDragStart({
        x: e.touches[0].clientX - offset.x,
        y: e.touches[0].clientY - offset.y,
      });
    }
  };

  const handleTouchMove = (e: React.TouchEvent<HTMLCanvasElement>) => {
    if (!isDragging || e.touches.length !== 1 || !imageRef.current) return;
    const rawOffset = {
      x: e.touches[0].clientX - dragStart.x,
      y: e.touches[0].clientY - dragStart.y,
    };
    const clamped = getClampedOffset(rawOffset, zoom, rotation, imageRef.current);
    setOffset(clamped);
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
  };

  // Xử lý cuộn chuột để zoom
  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    if (!imageRef.current) return;
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    const newZoom = Math.min(3.0, Math.max(1.0, +(zoom + delta).toFixed(2)));
    setZoom(newZoom);
    setOffset((prev) => getClampedOffset(prev, newZoom, rotation, imageRef.current!));
  };

  // Thay đổi thanh trượt Zoom
  const handleZoomChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!imageRef.current) return;
    const newZoom = parseFloat(e.target.value);
    setZoom(newZoom);
    setOffset((prev) => getClampedOffset(prev, newZoom, rotation, imageRef.current!));
  };

  // Xoay ảnh 90 độ
  const handleRotate = () => {
    if (!imageRef.current) return;
    const newRotation = (rotation + 90) % 360;
    setRotation(newRotation);
    setOffset((prev) => getClampedOffset(prev, zoom, newRotation, imageRef.current!));
  };

  // Đặt lại căn giữa
  const handleReset = () => {
    setZoom(1.0);
    setRotation(0);
    setOffset({ x: 0, y: 0 });
  };

  // Xuất ảnh cắt đạt chuẩn 1:1 512x512
  const handleApplyCrop = () => {
    const img = imageRef.current;
    if (!img) return;

    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = EXPORT_SIZE;
    exportCanvas.height = EXPORT_SIZE;
    const exportCtx = exportCanvas.getContext('2d');
    if (!exportCtx) return;

    exportCtx.imageSmoothingEnabled = true;
    exportCtx.imageSmoothingQuality = 'high';

    // Nền trắng cho các ảnh trong suốt PNG
    exportCtx.fillStyle = '#ffffff';
    exportCtx.fillRect(0, 0, EXPORT_SIZE, EXPORT_SIZE);

    const isRotated = rotation === 90 || rotation === 270;
    const effectiveW = isRotated ? img.height : img.width;
    const effectiveH = isRotated ? img.width : img.height;

    const baseScale = Math.max((CROP_RADIUS * 2) / effectiveW, (CROP_RADIUS * 2) / effectiveH);
    const totalScale = baseScale * zoom;

    // Tỉ lệ scale từ khung preview sang canvas xuất ảnh
    const exportRatio = EXPORT_SIZE / (CROP_RADIUS * 2);

    exportCtx.save();
    exportCtx.translate(
      EXPORT_SIZE / 2 + offset.x * exportRatio,
      EXPORT_SIZE / 2 + offset.y * exportRatio
    );
    exportCtx.rotate((rotation * Math.PI) / 180);
    exportCtx.scale(totalScale * exportRatio, totalScale * exportRatio);
    exportCtx.drawImage(img, -img.width / 2, -img.height / 2);
    exportCtx.restore();

    // Xuất ra file JPEG chất lượng cao 95%
    exportCanvas.toBlob(
      (blob) => {
        if (blob) {
          const croppedFile = new File([blob], 'avatar_cropped.jpg', {
            type: 'image/jpeg',
            lastModified: Date.now(),
          });
          const croppedPreviewUrl = URL.createObjectURL(blob);
          onCropComplete(croppedFile, croppedPreviewUrl);
        }
      },
      'image/jpeg',
      0.95
    );
  };

  return (
    <div className="crop-modal-backdrop" onClick={onClose}>
      <div className="crop-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="crop-modal-header">
          <h3 className="crop-modal-title">Cắt ảnh đại diện</h3>
          <button type="button" className="crop-modal-close" onClick={onClose} title="Đóng">
            ✕
          </button>
        </div>

        <div className="crop-modal-body">
          <div className="crop-canvas-wrapper">
            <canvas
              ref={canvasRef}
              width={CANVAS_SIZE}
              height={CANVAS_SIZE}
              className={`crop-canvas ${isDragging ? 'is-dragging' : ''}`}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onTouchStart={handleTouchStart}
              onTouchMove={handleTouchMove}
              onTouchEnd={handleTouchEnd}
              onWheel={handleWheel}
            />
          </div>

          <p className="crop-hint">
            💡 Kéo ảnh để căn chỉnh vị trí vào giữa vòng tròn. Cuộn chuột hoặc dùng thanh trượt để phóng to/thu nhỏ.
          </p>

          <div className="crop-controls">
            <div className="crop-zoom-control">
              <span className="crop-zoom-label">Thu phóng</span>
              <button
                type="button"
                className="crop-icon-btn"
                onClick={() => {
                  if (!imageRef.current) return;
                  const newZ = Math.max(1.0, +(zoom - 0.1).toFixed(2));
                  setZoom(newZ);
                  setOffset((p) => getClampedOffset(p, newZ, rotation, imageRef.current!));
                }}
                title="Thu nhỏ"
              >
                −
              </button>
              <input
                type="range"
                min="1.0"
                max="3.0"
                step="0.05"
                value={zoom}
                onChange={handleZoomChange}
                className="crop-slider"
              />
              <button
                type="button"
                className="crop-icon-btn"
                onClick={() => {
                  if (!imageRef.current) return;
                  const newZ = Math.min(3.0, +(zoom + 0.1).toFixed(2));
                  setZoom(newZ);
                  setOffset((p) => getClampedOffset(p, newZ, rotation, imageRef.current!));
                }}
                title="Phóng to"
              >
                +
              </button>
              <span className="crop-zoom-value">{Math.round(zoom * 100)}%</span>
            </div>

            <div className="crop-quick-actions">
              <button
                type="button"
                className="crop-action-btn"
                onClick={handleRotate}
                title="Xoay 90 độ theo chiều kim đồng hồ"
              >
                ↺ Xoay 90°
              </button>
              <button
                type="button"
                className="crop-action-btn"
                onClick={handleReset}
                title="Đặt lại vị trí ban đầu"
              >
                ⟲ Đặt lại
              </button>
            </div>
          </div>
        </div>

        <div className="crop-modal-footer">
          <button type="button" className="crop-cancel-btn" onClick={onClose}>
            Hủy
          </button>
          <button type="button" className="crop-apply-btn" onClick={handleApplyCrop}>
            ✓ Cắt & Áp dụng
          </button>
        </div>
      </div>
    </div>
  );
};
