import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import '../../App.css'
import { SeismicMap, type BlockClickInfo } from '../../components/SeismicMap'
import { CrsConfigModal } from '../../components/CrsConfigModal'
import { useSeismicData } from '../../hooks/useSeismicData'
import { useAuth } from '../auth/AuthContext'
import {
  loadWorkspace,
  useWorkspacePersistence,
  type SavedPolygon,
} from '../../hooks/useWorkspacePersistence'
import {
  exportSegySpatialFilter,
  subscribeSegyProgressWebSocket,
  type ExportSegyResult,
} from '../../api/seismicApi'
import { blocksApi } from '../../api/blocksApi'
import type { GeoJSONFeatureCollection, SegyHeaderInspectionResult, SplitCommand } from '../../types/api'

export const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [showUserDropdown, setShowUserDropdown] = useState(false)
  const userDropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userDropdownRef.current && !userDropdownRef.current.contains(event.target as Node)) {
        setShowUserDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  // Khôi phục workspace đã lưu của user này từ localStorage
  const initialWorkspace = useMemo(
    () => (user ? loadWorkspace(user.id) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [user?.id]
  )

  const [selectedFileIds, setSelectedFileIds] = useState<number[]>(
    () => initialWorkspace?.selectedFileIds ?? []
  )
  const [showLines, setShowLines] = useState<boolean>(
    () => initialWorkspace?.showLines ?? true
  )
  const [showPoints, setShowPoints] = useState<boolean>(
    () => initialWorkspace?.showPoints ?? true
  )
  const [showTraces, setShowTraces] = useState<boolean>(
    () => initialWorkspace?.showTraces ?? false
  )
  const [showDeleteModal, setShowDeleteModal] = useState(false)

  const [isDrawingPolygon, setIsDrawingPolygon] = useState(false)
  const [drawnPolygonRing, setDrawnPolygonRing] = useState<[number, number][] | null>(null)

  // Saved polygons
  const [savedPolygons, setSavedPolygons] = useState<SavedPolygon[]>(
    () => initialWorkspace?.savedPolygons ?? []
  )
  const [activePolygonIds, setActivePolygonIds] = useState<string[]>(
    () => initialWorkspace?.activePolygonIds ?? []
  )
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [pendingPolygonName, setPendingPolygonName] = useState('')
  const [pendingRing, setPendingRing] = useState<[number, number][] | null>(null)

  // ── Block States ─────────────────────────────────────────────────────────
  const [blockGeoJSON, setBlockGeoJSON] = useState<GeoJSONFeatureCollection | null>(null)
  const [showBlocks, setShowBlocks] = useState<boolean>(true)
  const [uploadingBlocks, setUploadingBlocks] = useState<boolean>(false)
  const [blockProgressPercent, setBlockProgressPercent] = useState<number>(0)
  const [blockProgressMessage, setBlockProgressMessage] = useState<string>('')
  const [blockError, setBlockError] = useState<string | null>(null)
  const [selectedBlockInfo, setSelectedBlockInfo] = useState<BlockClickInfo | null>(null)
  
  // ── Block Search States & Handlers ─────────────────────────────────────────
  const [blockSearchQuery, setBlockSearchQuery] = useState('')
  const [showBlockSuggestions, setShowBlockSuggestions] = useState(false)
  const [blockSearchError, setBlockSearchError] = useState<string | null>(null)
  const [focusedBlock, setFocusedBlock] = useState<{ code: string; timestamp: number } | null>(null)

  const matchingBlockSuggestions = useMemo(() => {
    if (!blockSearchQuery.trim() || !blockGeoJSON?.features) return []
    const query = blockSearchQuery.trim().toLowerCase()
    return blockGeoJSON.features
      .map((f) => f.properties?.block_code as string)
      .filter((code): code is string => Boolean(code) && code.toLowerCase().includes(query))
      .filter((value, index, self) => self.indexOf(value) === index)
      .slice(0, 8)
  }, [blockSearchQuery, blockGeoJSON])

  function handleExecuteBlockSearch(targetQuery: string) {
    const query = targetQuery.trim()
    if (!query) return
    setBlockSearchError(null)

    if (!blockGeoJSON?.features || blockGeoJSON.features.length === 0) {
      setBlockSearchError('Chưa có dữ liệu Lô địa chấn.')
      return
    }

    const feat =
      blockGeoJSON.features.find((f) => {
        const code = f.properties?.block_code
        return code && code.toString().toLowerCase() === query.toLowerCase()
      }) ||
      blockGeoJSON.features.find((f) => {
        const code = f.properties?.block_code
        return code && code.toString().toLowerCase().includes(query.toLowerCase())
      })

    if (!feat) {
      setBlockSearchError(`Không tìm thấy lô với mã "${query}"`)
      return
    }

    const foundCode = feat.properties?.block_code as string
    setBlockSearchQuery(foundCode)
    setShowBlockSuggestions(false)
    if (!showBlocks) {
      setShowBlocks(true)
    }
    setFocusedBlock({ code: foundCode, timestamp: Date.now() })
  }

  // Draggable Popup position state
  const [popupPos, setPopupPos] = useState<{ x: number; y: number } | null>(null)
  const [isExportingExcel, setIsExportingExcel] = useState<boolean>(false)

  const handleExportBlockExcel = async (blockInfo: BlockClickInfo) => {
    if (!blockInfo?.id) return
    try {
      setIsExportingExcel(true)
      await blocksApi.exportBlockExcel(blockInfo.id, blockInfo.block_code)
    } catch (err: any) {
      alert(err.message || 'Lỗi khi tải file Excel')
    } finally {
      setIsExportingExcel(false)
    }
  }
  const isDraggingRef = useRef<boolean>(false)
  const dragStartRef = useRef<{ mouseX: number; mouseY: number; popupX: number; popupY: number }>({
    mouseX: 0,
    mouseY: 0,
    popupX: 0,
    popupY: 0,
  })

  // Reset popup position to click location when selected block changes
  useEffect(() => {
    if (selectedBlockInfo) {
      const initX = Math.min(Math.max(selectedBlockInfo.pixel[0] + 10, 10), window.innerWidth - 300)
      const initY = Math.max(selectedBlockInfo.pixel[1] - 160, 20)
      setPopupPos({ x: initX, y: initY })
    } else {
      setPopupPos(null)
    }
  }, [selectedBlockInfo?.id, selectedBlockInfo?.pixel])

  const handleHeaderMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).tagName === 'BUTTON') return
    e.preventDefault()

    const currentX = popupPos?.x ?? (selectedBlockInfo ? Math.min(Math.max(selectedBlockInfo.pixel[0] + 10, 10), window.innerWidth - 300) : 10)
    const currentY = popupPos?.y ?? (selectedBlockInfo ? Math.max(selectedBlockInfo.pixel[1] - 160, 20) : 20)

    dragStartRef.current = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      popupX: currentX,
      popupY: currentY,
    }
    isDraggingRef.current = true

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!isDraggingRef.current) return
      const deltaX = moveEvent.clientX - dragStartRef.current.mouseX
      const deltaY = moveEvent.clientY - dragStartRef.current.mouseY

      const newX = Math.min(Math.max(dragStartRef.current.popupX + deltaX, 0), window.innerWidth - 280)
      const newY = Math.min(Math.max(dragStartRef.current.popupY + deltaY, 0), window.innerHeight - 100)

      setPopupPos({ x: newX, y: newY })
    }

    const handleMouseUp = () => {
      isDraggingRef.current = false
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
  }

  // Split Block state
  const [isSplittingBlock, setIsSplittingBlock] = useState<boolean>(false)
  const [splitLineCoords, setSplitLineCoords] = useState<[number, number][] | null>(null)
  const [showSplitConfirmModal, setShowSplitConfirmModal] = useState<boolean>(false)
  const [codeChildA, setCodeChildA] = useState<string>('')
  const [codeChildB, setCodeChildB] = useState<string>('')
  const [splitting, setSplitting] = useState<boolean>(false)

  // ── Command Pattern: Undo / Redo Stacks ───────────────────────────────────
  // undoStack: LIFO — các lệnh đã thực thi, có thể hoàn tác
  // redoStack: LIFO — các lệnh đã undo, có thể thực lại (redo)
  const [undoStack, setUndoStack] = useState<SplitCommand[]>([])
  const [redoStack, setRedoStack] = useState<SplitCommand[]>([])
  const [undoing, setUndoing] = useState<boolean>(false)
  const [redoing, setRedoing] = useState<boolean>(false)
  const [undoError, setUndoError] = useState<string | null>(null)

  // Fetch Blocks
  const fetchBlocks = async () => {
    try {
      const geojson = await blocksApi.getGeoJSON('active')
      setBlockGeoJSON(geojson)
    } catch (err: any) {
      console.error('Failed to load seismic blocks:', err)
    }
  }

  useEffect(() => {
    fetchBlocks()
  }, [])

  // Cancel split mode on ESC key + Ctrl+Z undo + Ctrl+Y / Ctrl+Shift+Z redo
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // ESC: hủy chế độ vẽ đường cắt
      if (e.key === 'Escape' && isSplittingBlock) {
        setIsSplittingBlock(false)
        setSplitLineCoords(null)
        return
      }
      // Ctrl+Z: hoàn tác tách lô
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey && !isSplittingBlock && undoStack.length > 0 && !undoing && !redoing) {
        e.preventDefault()
        handleUndoSplit()
        return
      }
      // Ctrl+Y hoặc Ctrl+Shift+Z: redo
      if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey)) && !isSplittingBlock && redoStack.length > 0 && !undoing && !redoing) {
        e.preventDefault()
        handleRedoSplit()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isSplittingBlock, undoStack, redoStack, undoing, redoing])

  // Persistence hook
  const { save } = useWorkspacePersistence(user?.id ?? null)

  useEffect(() => {
    save({ selectedFileIds, showLines, showPoints, showTraces, savedPolygons, activePolygonIds })
  }, [save, selectedFileIds, showLines, showPoints, showTraces, savedPolygons, activePolygonIds])

  const hydratedRef = useRef<number | null>(null)
  useEffect(() => {
    if (!user || hydratedRef.current === user.id) return
    hydratedRef.current = user.id
    const ws = loadWorkspace(user.id)
    setSelectedFileIds(ws.selectedFileIds)
    setShowLines(ws.showLines)
    setShowPoints(ws.showPoints)
    setShowTraces(ws.showTraces)
    setSavedPolygons(ws.savedPolygons)
    setActivePolygonIds(ws.activePolygonIds)
  }, [user])

  const {
    files,
    summary,
    layers,
    loading,
    uploading,
    progressMessage,
    progressPercent,
    deleting,
    exporting,
    exportError,
    error,
    inspectHeader,
    uploadFiles,
    deleteFiles,
    exportCsv,
  } = useSeismicData(selectedFileIds)
  const selectedFiles = files.filter((file) => selectedFileIds.includes(file.id))

  // ── CRS Selection Modal States ──────────────────────────────────────────
  const [showCrsModal, setShowCrsModal] = useState<boolean>(false)
  const [pendingSegyFiles, setPendingSegyFiles] = useState<File[]>([])
  const [inspectionResult, setInspectionResult] = useState<SegyHeaderInspectionResult | null>(null)
  const [inspectingHeader, setInspectingHeader] = useState<boolean>(false)

  async function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? [])
    event.target.value = ''
    if (selectedFiles.length === 0) return

    setPendingSegyFiles(selectedFiles)
    setShowCrsModal(true)
    setInspectingHeader(true)
    setInspectionResult(null)

    try {
      // Pre-inspect the first file's textual header to detect source CRS
      const result = await inspectHeader(selectedFiles[0])
      setInspectionResult(result)
    } catch (err: any) {
      console.warn('Lỗi khi inspect header SEG-Y:', err)
      // Fallback default inspection if inspection fails
      setInspectionResult({
        filename: selectedFiles[0].name,
        source_crs: 'EPSG:4326',
        source_crs_name: 'WGS 84 (Mặc định)',
        default_target_crs: 'EPSG:4326',
        default_target_crs_name: 'WGS 84 (Kinh độ / Vĩ độ - EPSG:4326)',
        trace_count: 0,
        textual_header_preview: null,
      })
    } finally {
      setInspectingHeader(false)
    }
  }

  async function handleConfirmCrsUpload(sourceCrs: string, targetCrs: string) {
    if (pendingSegyFiles.length === 0) return
    setShowCrsModal(false)

    try {
      const fileIds = await uploadFiles(pendingSegyFiles, sourceCrs, targetCrs)
      if (fileIds.length > 0) setSelectedFileIds(fileIds)
    } catch {
      // Error handled by hook
    } finally {
      setPendingSegyFiles([])
      setInspectionResult(null)
    }
  }

  async function handleBlockFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? [])
    event.target.value = ''
    if (selectedFiles.length === 0) return

    setUploadingBlocks(true)
    setBlockProgressPercent(10)
    setBlockProgressMessage('Đang chuẩn bị nạp file Shapefile .zip...')
    setBlockError(null)

    const clientId = `client_${Math.random().toString(36).substring(2, 9)}_${Date.now()}`
    const taskId = `block_${Math.random().toString(36).substring(2, 9)}_${Date.now()}`
    let isFinished = false

    // 1. Subscribe to WebSocket updates
    const wsUnsub = subscribeSegyProgressWebSocket(clientId, (msg) => {
      if (msg.task_id === taskId) {
        if (typeof msg.progress_percent === 'number') {
          setBlockProgressPercent(msg.progress_percent)
        }
        if (msg.message) {
          setBlockProgressMessage(msg.message)
        }
        if (msg.status === 'COMPLETED' || msg.status === 'FAILED') {
          isFinished = true
        }
      }
    })

    // 2. Fallback polling every 500ms
    const pollInterval = setInterval(async () => {
      if (isFinished) return
      try {
        const taskData = await blocksApi.fetchBlockTaskStatus(taskId)
        if (taskData) {
          if (typeof taskData.progress_percent === 'number') {
            setBlockProgressPercent(taskData.progress_percent)
          }
          if (taskData.message) {
            setBlockProgressMessage(taskData.message)
          }
          if (taskData.status === 'COMPLETED' || taskData.status === 'FAILED') {
            isFinished = true
          }
        }
      } catch {
        // ignore polling errors
      }
    }, 500)

    try {
      await blocksApi.uploadZip(selectedFiles[0], taskId)
      setBlockProgressPercent(100)
      setBlockProgressMessage('Đã nạp thành công Lô địa chấn!')
      await fetchBlocks()
    } catch (err: any) {
      setBlockError(err?.message || 'Lỗi khi tải lên file Block')
    } finally {
      isFinished = true
      clearInterval(pollInterval)
      wsUnsub()
      setTimeout(() => {
        setUploadingBlocks(false)
        setBlockProgressPercent(0)
        setBlockProgressMessage('')
      }, 600)
    }
  }

  const [deleteBlockTarget, setDeleteBlockTarget] = useState<{ name: string; rawSource: string; count: number } | null>(null)
  const [showDeleteBlockModal, setShowDeleteBlockModal] = useState<boolean>(false)
  const [deletingBlocks, setDeletingBlocks] = useState<boolean>(false)

  // Group processed block files from blockGeoJSON
  const processedBlockFiles = useMemo(() => {
    if (!blockGeoJSON || blockGeoJSON.features.length === 0) return []

    const fileMap = new Map<string, { name: string; count: number; rawSource: string }>()

    for (const feat of blockGeoJSON.features) {
      const src = (feat.properties?.source_file as string) || 'Vietnam_Seismic_Blocks.zip'
      const rawBasename = src.split(/[/\\]/).pop() || 'Vietnam_Seismic_Blocks.zip'
      const cleanName = rawBasename
        .replace(/^[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}_/i, '')
        .replace(/^[a-f0-9]{32}_/i, '')

      const existing = fileMap.get(cleanName)
      if (existing) {
        existing.count++
      } else {
        fileMap.set(cleanName, {
          name: cleanName,
          count: 1,
          rawSource: src,
        })
      }
    }

    return Array.from(fileMap.values())
  }, [blockGeoJSON])

  const handleConfirmDeleteBlockFile = async () => {
    if (!deleteBlockTarget) return
    setDeletingBlocks(true)
    try {
      await blocksApi.deleteBlocks(deleteBlockTarget.rawSource)
      await fetchBlocks()
      setShowDeleteBlockModal(false)
      setDeleteBlockTarget(null)
    } catch (err: any) {
      setBlockError(err?.message || 'Lỗi khi xóa file Block')
    } finally {
      setDeletingBlocks(false)
    }
  }

  function handleSelectAll() {
    setSelectedFileIds(files.map((file) => file.id))
  }

  function handleDeselectAll() {
    setSelectedFileIds([])
  }

  async function handleConfirmDelete() {
    if (selectedFileIds.length === 0) return
    try {
      await deleteFiles(selectedFileIds)
      setSelectedFileIds([])
      setShowDeleteModal(false)
    } catch {
      // Error handled by hook
    }
  }

  function handlePolygonFinish(ring: [number, number][]) {
    setDrawnPolygonRing(ring)
    setIsDrawingPolygon(false)
  }

  async function handleExportCsv() {
    if (selectedFileIds.length === 0 || exporting) return
    try {
      await exportCsv(selectedFileIds)
    } catch {
      // exportError is already set by the hook
    }
  }

  function handleSavePolygonClick() {
    if (!drawnPolygonRing) return
    setPendingRing(drawnPolygonRing)
    setPendingPolygonName('')
    setShowSaveModal(true)
  }

  function handleConfirmSavePolygon() {
    if (!pendingRing) return
    const name = pendingPolygonName.trim() || `Polygon ${savedPolygons.length + 1}`
    const newPolygon: SavedPolygon = {
      id: Date.now().toString(),
      name,
      ring: pendingRing,
    }
    setSavedPolygons((prev) => [...prev, newPolygon])
    setActivePolygonIds((prev) => [...prev, newPolygon.id])
    setShowSaveModal(false)
    setPendingRing(null)
    setPendingPolygonName('')
    setDrawnPolygonRing(null)
  }

  function handleToggleSavedPolygon(id: string) {
    setActivePolygonIds((prev) =>
      prev.includes(id) ? prev.filter((pid) => pid !== id) : [...prev, id]
    )
  }

  function handleDeleteSavedPolygon(id: string) {
    setSavedPolygons((prev) => prev.filter((p) => p.id !== id))
    setActivePolygonIds((prev) => prev.filter((pid) => pid !== id))
  }

  // ── Block Action Handlers ──────────────────────────────────────────────────
  function handleFilterByBlock(info: BlockClickInfo) {
    if (!info.polygonRing || info.polygonRing.length < 3) return
    const polygonId = `block-${info.id}`
    const name = info.block_code

    const existing = savedPolygons.find((p) => p.id === polygonId)
    if (!existing) {
      const newPoly: SavedPolygon = {
        id: polygonId,
        name,
        ring: info.polygonRing,
      }
      setSavedPolygons((prev) => [...prev, newPoly])
    }
    if (!activePolygonIds.includes(polygonId)) {
      setActivePolygonIds((prev) => [...prev, polygonId])
    }
  }

  function handleStartSplitBlock(info: BlockClickInfo) {
    setSelectedBlockInfo(info)
    setIsSplittingBlock(true)
    setSplitLineCoords(null)
    setCodeChildA(`${info.block_code}-A`)
    setCodeChildB(`${info.block_code}-B`)
  }

  function handleSplitLineFinish(coords: [number, number][]) {
    setSplitLineCoords(coords)
    setShowSplitConfirmModal(true)
  }

  async function handleConfirmSplitBlock() {
    if (!selectedBlockInfo || !splitLineCoords || splitLineCoords.length !== 2) return
    setSplitting(true)
    setBlockError(null)

    const wkt = `LINESTRING(${splitLineCoords[0][0]} ${splitLineCoords[0][1]}, ${splitLineCoords[1][0]} ${splitLineCoords[1][1]})`
    const codes = [codeChildA.trim(), codeChildB.trim()].filter(Boolean)

    try {
      const childBlocks = await blocksApi.splitBlock(selectedBlockInfo.id, {
        split_line_wkt: wkt,
        new_block_codes: codes.length > 0 ? codes : undefined,
      })

      // ── Command Pattern: push lệnh vào Undo Stack, xóa Redo Stack ────────
      const command: SplitCommand = {
        parentBlockId: selectedBlockInfo.id,
        parentBlockCode: selectedBlockInfo.block_code,
        childIds: childBlocks.map((b) => b.id),
        splitLineWkt: wkt,
        newBlockCodes: codes,
      }
      setUndoStack((prev) => [...prev, command])
      setRedoStack([])  // thực hiện mới → xóa redo stack
      setUndoError(null)
      // ───────────────────────────────────────────────────────────────────

      setShowSplitConfirmModal(false)
      setIsSplittingBlock(false)
      setSplitLineCoords(null)
      setSelectedBlockInfo(null)
      await fetchBlocks()
    } catch (err: any) {
      setBlockError(err?.message || 'Không thể chia Lô. Vui lòng kiểm tra lại đường cắt.')
    } finally {
      setSplitting(false)
    }
  }

  // ── Command Pattern: Undo ─────────────────────────────────────────────────
  async function handleUndoSplit() {
    if (undoStack.length === 0 || undoing || redoing) return
    const command = undoStack[undoStack.length - 1]
    setUndoing(true)
    setUndoError(null)
    try {
      await blocksApi.undoSplit(command.parentBlockId)
      // Pop khỏi undoStack và push vào redoStack
      setUndoStack((prev) => prev.slice(0, -1))
      setRedoStack((prev) => [...prev, command])
      await fetchBlocks()
    } catch (err: any) {
      setUndoError(err?.message || `Không thể hoàn tác tách lô "${command.parentBlockCode}"`)
    } finally {
      setUndoing(false)
    }
  }

  // ── Command Pattern: Redo — execute() lại lệnh đã undo ──────────────────
  async function handleRedoSplit() {
    if (redoStack.length === 0 || undoing || redoing) return
    const command = redoStack[redoStack.length - 1]
    setRedoing(true)
    setUndoError(null)
    try {
      // execute(): gọi lại splitBlock với đúng wkt + codes
      const childBlocks = await blocksApi.splitBlock(command.parentBlockId, {
        split_line_wkt: command.splitLineWkt,
        new_block_codes: command.newBlockCodes.length > 0 ? command.newBlockCodes : undefined,
      })
      // Cập nhật command với childIds mới (có thể khác lần trước)
      const updatedCommand: SplitCommand = {
        ...command,
        childIds: childBlocks.map((b) => b.id),
      }
      // Pop khỏi redoStack và push vào undoStack
      setRedoStack((prev) => prev.slice(0, -1))
      setUndoStack((prev) => [...prev, updatedCommand])
      await fetchBlocks()
    } catch (err: any) {
      setUndoError(err?.message || `Không thể thực lại tách lô "${command.parentBlockCode}"`)
    } finally {
      setRedoing(false)
    }
  }

  const [exportingSegyId, setExportingSegyId] = useState<string | null>(null)
  const [segyExportError, setSegyExportError] = useState<string | null>(null)
  const [exportModalResults, setExportModalResults] = useState<ExportSegyResult[] | null>(null)

  async function handleExportPolygonSegy(poly: { id: string; name: string; ring: [number, number][] }) {
    if (exportingSegyId) return
    setExportingSegyId(poly.id)
    setSegyExportError(null)
    try {
      const activeCrs = selectedFiles[0]?.source_crs
      const results = await exportSegySpatialFilter(poly.ring, poly.name, selectedFileIds, activeCrs)
      if (results.length === 0) {
        setSegyExportError(`Không tìm thấy đoạn line nào nằm trong polygon "${poly.name}"`)
      } else if (results.length === 1) {
        const link = document.createElement('a')
        link.href = results[0].download_url
        link.download = results[0].filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      } else {
        results.forEach((res, index) => {
          setTimeout(() => {
            const link = document.createElement('a')
            link.href = res.download_url
            link.download = res.filename
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
          }, index * 300)
        })
        setExportModalResults(results)
      }
    } catch (err: any) {
      setSegyExportError(err?.message || 'Xuất file SEG-Y thất bại')
    } finally {
      setExportingSegyId(null)
    }
  }

  // Merge active saved polygon rings for map display
  const activePolygonRings = activePolygonIds
    .map((id) => savedPolygons.find((p) => p.id === id)?.ring)
    .filter((r): r is [number, number][] => Boolean(r))

  const activeBlockCount = blockGeoJSON?.features.length ?? 0

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">WEBGIS / DỊCH VỤ DỮ LIỆU</span>
          <h1>Seismic field atlas</h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {user && (
            <div className="user-dropdown-container" ref={userDropdownRef}>
              <button
                type="button"
                className={`user-dropdown-btn ${showUserDropdown ? 'active' : ''}`}
                onClick={() => setShowUserDropdown((prev) => !prev)}
                aria-expanded={showUserDropdown}
              >
                <div className="user-dropdown-avatar">
                  {user.avatar_url ? (
                    <img src={user.avatar_url} alt={user.full_name} className="avatar-img-sm" />
                  ) : (
                    <span>{user.full_name ? user.full_name[0].toUpperCase() : 'U'}</span>
                  )}
                </div>
                <span className="user-dropdown-name">{user.full_name || user.email}</span>
                <span className="user-dropdown-caret">{showUserDropdown ? '▲' : '▼'}</span>
              </button>

              {showUserDropdown && (
                <div className="user-dropdown-menu">
                  <div className="user-dropdown-header">
                    <div className="user-dropdown-header-name">{user.full_name}</div>
                    <div className="user-dropdown-header-email">{user.email}</div>
                    <span className={`role-tag ${user.role}`}>
                      {user.role === 'admin' ? 'Quản trị viên' : 'Người dùng'}
                    </span>
                  </div>
                  <div className="user-dropdown-divider" />
                  <button
                    type="button"
                    className="user-dropdown-item"
                    onClick={() => {
                      setShowUserDropdown(false)
                      navigate('/profile')
                    }}
                  >
                    <span className="menu-icon">👤</span>
                    <span>Thông tin cá nhân</span>
                  </button>
                  <button
                    type="button"
                    className="user-dropdown-item logout-item"
                    onClick={() => {
                      setShowUserDropdown(false)
                      handleLogout()
                    }}
                  >
                    <span className="menu-icon">🚪</span>
                    <span>Đăng xuất</span>
                  </button>
                </div>
              )}
            </div>
          )}
          <span className="connection">
            <i /> Đã kết nối PostGIS
          </span>
        </div>
      </header>

      <section className="workspace">
        <aside className="sidebar">
          {/* UPLOAD SECTION */}
          <label className="field-label" htmlFor="file-upload">
            Tải lên file SEG-Y
          </label>
          <label
            className={`upload-button${uploading ? ' is-uploading' : ''}`}
            htmlFor="file-upload"
          >
            <span>{uploading ? 'Đang xử lý...' : 'Chọn file .sgy'}</span>
            <b>+</b>
          </label>
          <input
            id="file-upload"
            className="sr-only"
            type="file"
            accept=".sgy,application/octet-stream"
            multiple
            disabled={uploading}
            onChange={handleFileUpload}
          />
          <small className="upload-hint">File được gửi đến máy chủ để xử lý.</small>

          {/* BLOCK UPLOAD BUTTON */}
          <label
            className={`upload-button upload-button--block${uploadingBlocks ? ' is-uploading' : ''}`}
            htmlFor="block-file-upload"
            style={{ marginTop: '8px' }}
          >
            <span>{uploadingBlocks ? 'Đang xử lý lô...' : 'Chọn file lô .zip'}</span>
            <b>+</b>
          </label>
          <input
            id="block-file-upload"
            className="sr-only"
            type="file"
            accept=".zip,.geojson"
            disabled={uploadingBlocks}
            onChange={handleBlockFileUpload}
          />
          <small className="upload-hint">Hỗ trợ Shapefile nén .zip hoặc GeoJSON ranh giới lô.</small>
          {blockError && <div className="error" style={{ fontSize: '0.75rem', marginTop: '4px' }}>{blockError}</div>}

          <div className="surveys-header">
            <label className="field-label" htmlFor="file-select">
              Khảo sát đã xử lý
            </label>
            {files.length > 0 && (
              <div className="surveys-actions">
                <button type="button" className="action-link" onClick={handleSelectAll}>
                  Tất cả
                </button>
                <button type="button" className="action-link" onClick={handleDeselectAll}>
                  Bỏ chọn
                </button>
              </div>
            )}
          </div>
          <select
            id="file-select"
            multiple
            size={5}
            value={selectedFileIds.map(String)}
            onChange={(event) =>
              setSelectedFileIds(
                Array.from(event.target.selectedOptions, (option) => Number(option.value))
              )
            }
          >
            {files.map((file) => (
              <option key={file.id} value={file.id}>
                {file.label}
              </option>
            ))}
          </select>

          {selectedFiles.length > 0 && (
            <>
              <div className="file-status">
                <span style={{ background: '#e4572e' }} />
                <strong>Đã chọn {selectedFiles.length}</strong>
                <small>hệ tọa độ EPSG:4326</small>
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
              <button
                type="button"
                className={`export-button${exporting ? ' is-exporting' : ''}`}
                disabled={exporting}
                onClick={handleExportCsv}
                title={`Xuất ${selectedFiles.length} file đã chọn sang CSV`}
              >
                <span>{exporting ? 'Đang xuất...' : `Xuất ${selectedFiles.length} file đã chọn`}</span>
                <b>⤓</b>
              </button>
            </>
          )}

          {/* PROCESSED BLOCK FILE SECTION */}
          <div className="surveys-header" style={{ marginTop: '12px' }}>
            <label className="field-label">
              File lô đã xử lý
            </label>
          </div>

          {processedBlockFiles.length > 0 ? (
            <div className="processed-block-list">
              {processedBlockFiles.map((bFile) => (
                <div key={bFile.name} className="processed-block-card">
                  <div className="processed-block-info">
                    <span className="block-file-icon">📦</span>
                    <div className="block-file-text">
                      <strong>{bFile.name}</strong>
                      <small>{bFile.count} Lô địa chấn</small>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="delete-button delete-button--block"
                    disabled={deletingBlocks}
                    onClick={() => {
                      setDeleteBlockTarget(bFile)
                      setShowDeleteBlockModal(true)
                    }}
                    title={`Xóa file ${bFile.name}`}
                  >
                    <span>{deletingBlocks ? 'Đang xóa...' : 'Xóa file lô'}</span>
                    <b>✕</b>
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-block-hint">
              <small>Chưa có file .zip block nào được xử lý.</small>
            </div>
          )}

          <div className="rule" />
          <p className="section-label">Bộ lọc không gian</p>

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
              <button type="button" className="btn-save-polygon" onClick={handleSavePolygonClick}>
                <span>Lưu</span>
                <b>💾</b>
              </button>
              <button
                type="button"
                className="btn-clear-polygon"
                onClick={() => {
                  setDrawnPolygonRing(null)
                  setIsDrawingPolygon(false)
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

          {/* Saved Polygons List */}
          {savedPolygons.length > 0 && (
            <div className="saved-polygons-list">
              {savedPolygons.map((poly) => {
                const isActive = activePolygonIds.includes(poly.id)
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
                      className="saved-polygon-export"
                      disabled={exportingSegyId === poly.id}
                      onClick={() => handleExportPolygonSegy(poly)}
                      title="Xuất các tuyến địa chấn trong polygon ra file SEG-Y (.sgy)"
                    >
                      {exportingSegyId === poly.id ? '⏳' : '⤓ .sgy'}
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
                )
              })}
            </div>
          )}
          {segyExportError && (
            <div className="error" style={{ marginTop: '8px', fontSize: '0.8rem' }}>
              {segyExportError}
            </div>
          )}

          <div className="rule" />
          <p className="section-label">Tìm kiếm lô địa chấn</p>
          <div className="block-search-container">
            <div className="block-search-input-wrapper">
              <input
                type="text"
                className="block-search-input"
                placeholder="Nhập mã lô (ví dụ: MVHN-01KT)..."
                value={blockSearchQuery}
                onChange={(e) => {
                  setBlockSearchQuery(e.target.value)
                  setShowBlockSuggestions(true)
                  setBlockSearchError(null)
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleExecuteBlockSearch(blockSearchQuery)
                  }
                }}
                onFocus={() => setShowBlockSuggestions(true)}
              />
              {blockSearchQuery ? (
                <button
                  type="button"
                  className="block-search-clear-btn"
                  onClick={() => {
                    setBlockSearchQuery('')
                    setBlockSearchError(null)
                    setShowBlockSuggestions(false)
                  }}
                  title="Xóa tìm kiếm"
                >
                  ✕
                </button>
              ) : (
                <span className="block-search-icon">🔍</span>
              )}
            </div>

            {showBlockSuggestions && matchingBlockSuggestions.length > 0 && (
              <ul className="block-search-suggestions">
                {matchingBlockSuggestions.map((blockCode) => (
                  <li
                    key={blockCode}
                    onClick={() => {
                      setBlockSearchQuery(blockCode)
                      setShowBlockSuggestions(false)
                      handleExecuteBlockSearch(blockCode)
                    }}
                  >
                    <span className="block-icon">📦</span>
                    <strong>{blockCode}</strong>
                  </li>
                ))}
              </ul>
            )}

            {blockSearchError && (
              <div className="block-search-error">{blockSearchError}</div>
            )}
          </div>

          <div className="rule" />
          <p className="section-label">Các lớp bản đồ</p>
          <label className="toggle">
            <input
              type="checkbox"
              checked={showBlocks}
              onChange={(event) => setShowBlocks(event.target.checked)}
            />
            <span>Lô địa chấn</span>
            <b>{activeBlockCount}</b>
          </label>
          <label className="toggle">
            <input
              type="checkbox"
              checked={showLines}
              onChange={(event) => setShowLines(event.target.checked)}
            />
            <span>Tuyến địa chấn</span>
            <b>{summary?.processed_line_count ?? 0}</b>
          </label>
          <label className="toggle">
            <input
              type="checkbox"
              checked={showPoints}
              onChange={(event) => setShowPoints(event.target.checked)}
            />
            <span>Điểm nổ</span>
            <b>{summary?.processed_shot_point_count ?? 0}</b>
          </label>
          <label className="toggle">
            <input
              type="checkbox"
              checked={showTraces}
              onChange={(event) => setShowTraces(event.target.checked)}
            />
            <span>Vết địa chấn</span>
            <b>{summary?.processed_trace_count ?? 0}</b>
          </label>

          <div className="sidebar-footer">
            <span>Cổng API</span>
            <code>localhost:8001</code>
          </div>
        </aside>

        <div className="map-panel">
          {/* FLOATING BANNER FOR SPLIT BLOCK MODE */}
          {isSplittingBlock && (
            <div className="floating-banner">
              <span>✂️ Click 2 điểm để vẽ một đường cắt ngang qua Lô [Nhấn ESC để hủy]</span>
              <button
                type="button"
                className="banner-close-btn"
                onClick={() => {
                  setIsSplittingBlock(false)
                  setSplitLineCoords(null)
                }}
              >
                ✕
              </button>
            </div>
          )}

          {/* ── UNDO / REDO FLOATING CONTROLS (góc trên phải map) ──────── */}
          {(undoStack.length > 0 || redoStack.length > 0) && (
            <div className="map-history-controls">
              <button
                id="btn-undo-split"
                type="button"
                className={`map-history-btn${undoStack.length === 0 || undoing || redoing ? ' is-disabled' : ''}${undoing ? ' is-active' : ''}`}
                disabled={undoStack.length === 0 || undoing || redoing}
                onClick={handleUndoSplit}
                title={undoStack.length > 0
                  ? `Undo: phục hồi "${undoStack[undoStack.length - 1].parentBlockCode}" (Ctrl+Z)`
                  : 'Không có thao tác để Undo'}
                aria-label="Undo tách lô"
              >
                {undoing ? (
                  <span className="map-history-spinner" />
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 7v6h6" />
                    <path d="M3 13C5.5 7.5 11 4 17 5.5a9 9 0 0 1 4 14" />
                  </svg>
                )}
              </button>
              <button
                id="btn-redo-split"
                type="button"
                className={`map-history-btn${redoStack.length === 0 || undoing || redoing ? ' is-disabled' : ''}${redoing ? ' is-active' : ''}`}
                disabled={redoStack.length === 0 || undoing || redoing}
                onClick={handleRedoSplit}
                title={redoStack.length > 0
                  ? `Redo: tách lại "${redoStack[redoStack.length - 1].parentBlockCode}" (Ctrl+Y)`
                  : 'Không có thao tác để Redo'}
                aria-label="Redo tách lô"
              >
                {redoing ? (
                  <span className="map-history-spinner" />
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 7v6h-6" />
                    <path d="M21 13C18.5 7.5 13 4 7 5.5a9 9 0 0 0-4 14" />
                  </svg>
                )}
              </button>
              {undoError && (
                <div className="map-history-error">{undoError}</div>
              )}
            </div>
          )}

          <SeismicMap
            data={layers}
            blockData={blockGeoJSON}
            files={files}
            showLines={showLines}
            showPoints={showPoints}
            showTraces={showTraces}
            showBlocks={showBlocks}
            selectedBlockId={selectedBlockInfo?.id ?? null}
            isDrawingPolygon={isDrawingPolygon}
            drawnPolygonRing={drawnPolygonRing}
            savedPolygonRings={activePolygonRings}
            onPolygonFinish={handlePolygonFinish}
            onBlockClick={(info) => setSelectedBlockInfo(info)}
            isSplittingBlock={isSplittingBlock}
            splitLineCoords={splitLineCoords}
            onSplitLineFinish={handleSplitLineFinish}
            focusedBlock={focusedBlock}
            mvtFileIds={selectedFileIds}
          />

          {/* POPUP FOR CLICKED BLOCK */}
          {selectedBlockInfo && !isSplittingBlock && popupPos && (
            <div
              className="block-popup"
              style={{
                left: popupPos.x,
                top: popupPos.y,
              }}
            >
              <div
                className="block-popup-header"
                onMouseDown={handleHeaderMouseDown}
                title="Kéo thả để di chuyển khung popup"
              >
                <div className="block-popup-header-title">
                  <span className="drag-handle-dots" title="Kéo để di chuyển">⋮⋮</span>
                  <strong>{selectedBlockInfo.block_code}</strong>
                </div>
                <button
                  type="button"
                  className="popup-close-btn"
                  onClick={() => setSelectedBlockInfo(null)}
                >
                  ✕
                </button>
              </div>

              <div className="block-popup-body">
                <div className="block-popup-row">
                  <span>Bể trầm tích:</span>
                  <b>{selectedBlockInfo.basin_name || 'Chưa xác định'}</b>
                </div>
                <div className="block-popup-row">
                  <span>Diện tích:</span>
                  <b>{selectedBlockInfo.area_km2 ? `${selectedBlockInfo.area_km2} km²` : 'Chưa có dữ liệu'}</b>
                </div>
                <div className="block-popup-row">
                  <span>Nhà thầu:</span>
                  <b>{selectedBlockInfo.operator || 'Chưa xác định'}</b>
                </div>
                <div className="block-popup-row">
                  <span>Số tuyến 2D cắt qua:</span>
                  <b>{selectedBlockInfo.intersectingLineCount} tuyến</b>
                </div>
              </div>

              <div className="block-popup-actions">
                <button
                  type="button"
                  className="btn-export-excel-block"
                  onClick={() => handleExportBlockExcel(selectedBlockInfo)}
                  disabled={isExportingExcel}
                >
                  {isExportingExcel ? '⏳ Đang xuất...' : '📊 Tải về dữ liệu lô này'}
                </button>
                <button
                  type="button"
                  className="btn-filter-block"
                  onClick={() => handleFilterByBlock(selectedBlockInfo)}
                >
                  🔍 Dùng làm bộ lọc không gian
                </button>
                <button
                  type="button"
                  className="btn-split-block"
                  onClick={() => handleStartSplitBlock(selectedBlockInfo)}
                >
                  ✂️ Phân tách lô này
                </button>
              </div>
            </div>
          )}

          {selectedFileIds.length === 0 && activeBlockCount === 0 && (
            <div className="map-empty">
              <span>⌁</span>
              <strong>Chọn khảo sát hoặc tải lên file lô</strong>
              <small>Dữ liệu hình học sau khi xử lý sẽ hiển thị tại đây</small>
            </div>
          )}
          {uploading && (
            <div className="upload-progress-overlay">
              <div className="upload-progress-box">
                <div className="upload-progress-header">
                  <span className="upload-spinner" />
                  <strong>Đang xử lý dữ liệu SEG-Y...</strong>
                </div>
                <div className="upload-progress-bar-container">
                  <div
                    className="upload-progress-bar-fill"
                    style={{ width: `${Math.max(progressPercent, 10)}%` }}
                  />
                </div>
                <div className="upload-progress-status">
                  <small>{progressMessage || 'Đang stream dữ liệu lên server...'}</small>
                  <span>{progressPercent}%</span>
                </div>
              </div>
            </div>
          )}
          {uploadingBlocks && (
            <div className="upload-progress-overlay">
              <div className="upload-progress-box">
                <div className="upload-progress-header">
                  <span className="upload-spinner" />
                  <strong>Đang xử lý file Lô địa chấn (.zip)...</strong>
                </div>
                <div className="upload-progress-bar-container">
                  <div
                    className="upload-progress-bar-fill"
                    style={{ width: `${Math.max(blockProgressPercent, 10)}%` }}
                  />
                </div>
                <div className="upload-progress-status">
                  <small>{blockProgressMessage || 'Đang nạp dữ liệu Shapefile lên server...'}</small>
                  <span>{blockProgressPercent}%</span>
                </div>
              </div>
            </div>
          )}
          {loading && <div className="loading">Đang tải dữ liệu...</div>}
          {error && <div className="error">{error}</div>}
          {exportError && <div className="error">{exportError}</div>}

          {/* MAP LEGEND AT BOTTOM */}
          <div className="map-legend">
            {drawnPolygonRing || activePolygonRings.length > 0 ? (
              <>
                <span>
                  <i className="line-key line-inside-key" /> Bên trong (Xanh)
                </span>
                <span>
                  <i className="line-key line-outside-key" /> Bên ngoài (Đỏ)
                </span>
              </>
            ) : (
              <span>
                <i className="line-key" /> Tuyến địa chấn
              </span>
            )}
            <span>
              <i className="point-key" /> Điểm nổ
            </span>
            <span>
              <i className="trace-key" /> Vết địa chấn
            </span>
            <span>
              <i className="block-key" /> Ranh giới Lô
            </span>
          </div>
        </div>
      </section>

      <footer className="summary">
        <div>
          <span className="eyebrow">TẬP DỮ LIỆU ĐÃ CHỌN</span>
          <strong>{summary?.filename ?? 'Chưa chọn khảo sát nào'}</strong>
        </div>
        <div className="metrics">
          <span>
            <b>{summary?.processed_line_count ?? 0}</b> tuyến
          </span>
          <span>
            <b>{summary?.processed_shot_point_count ?? 0}</b> điểm nổ
          </span>
          <span>
            <b>{summary?.processed_trace_count ?? 0}</b> trace
          </span>
          <span>
            <b>{activeBlockCount}</b> lô
          </span>
        </div>
      </footer>

      {/* Delete SEG-Y modal */}
      {showDeleteModal && (
        <div className="modal-backdrop" onClick={() => !deleting && setShowDeleteModal(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Xác nhận xóa dữ liệu SEG-Y</h3>
            <p>
              Bạn có chắc chắn muốn xóa <strong>{selectedFiles.length}</strong> file dữ liệu thừa đã chọn? Thao tác này sẽ xóa vĩnh viễn các file và toàn bộ hình học liên quan khỏi hệ thống.
            </p>
            <ul className="modal-file-list">
              {selectedFiles.map((file) => (
                <li key={file.id}>
                  • {file.filename} (#{file.id})
                </li>
              ))}
            </ul>
            <div className="modal-actions">
              <button
                type="button"
                className="btn-cancel"
                disabled={deleting}
                onClick={() => setShowDeleteModal(false)}
              >
                Hủy
              </button>
              <button
                type="button"
                className="btn-delete-confirm"
                disabled={deleting}
                onClick={handleConfirmDelete}
              >
                {deleting ? 'Đang xóa...' : 'Xóa dữ liệu'}
              </button>
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
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleConfirmSavePolygon()
                if (e.key === 'Escape') setShowSaveModal(false)
              }}
            />
            <div className="modal-actions">
              <button type="button" className="btn-cancel" onClick={() => setShowSaveModal(false)}>
                Hủy
              </button>
              <button type="button" className="btn-save-confirm" onClick={handleConfirmSavePolygon}>
                Lưu polygon
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CONFIRMATION MODAL FOR SPLIT BLOCK */}
      {showSplitConfirmModal && selectedBlockInfo && (
        <div className="modal-backdrop" onClick={() => !splitting && setShowSplitConfirmModal(false)}>
          <div className="modal-box modal-box--split" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ color: '#f59e0b', margin: '0 0 10px' }}>✂️ Xác nhận chia Lô này thành 2 phần?</h3>
            <p>
              Lô gốc <strong>{selectedBlockInfo.block_code}</strong> sẽ được chia thành 2 lô con với đường cắt vừa vẽ. Vui lòng kiểm tra hoặc đổi tên cho 2 lô mới:
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
              <div>
                <label className="field-label" style={{ display: 'block', marginBottom: '4px' }}>Mã Lô 1 (Phần A)</label>
                <input
                  type="text"
                  className="polygon-name-input"
                  style={{ margin: 0 }}
                  value={codeChildA}
                  onChange={(e) => setCodeChildA(e.target.value)}
                />
              </div>
              <div>
                <label className="field-label" style={{ display: 'block', marginBottom: '4px' }}>Mã Lô 2 (Phần B)</label>
                <input
                  type="text"
                  className="polygon-name-input"
                  style={{ margin: 0 }}
                  value={codeChildB}
                  onChange={(e) => setCodeChildB(e.target.value)}
                />
              </div>
            </div>
            <div className="modal-actions">
              <button
                type="button"
                className="btn-cancel"
                disabled={splitting}
                onClick={() => {
                  setShowSplitConfirmModal(false)
                  setSplitLineCoords(null)
                }}
              >
                Hủy
              </button>
              <button
                type="button"
                className="btn-save-confirm"
                style={{ background: '#f59e0b', borderColor: '#d97706' }}
                disabled={splitting}
                onClick={handleConfirmSplitBlock}
              >
                {splitting ? 'Đang phân tách...' : 'Xác nhận chia Lô'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Export SEG-Y results modal */}
      {exportModalResults && (
        <div className="modal-backdrop" onClick={() => setExportModalResults(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Kết quả xuất dữ liệu SEG-Y (.sgy)</h3>
            <p>
              Đã tạo thành công <strong>{exportModalResults.length}</strong> file SEG-Y cho các đường line được cắt bởi polygon.
            </p>
            <ul className="modal-file-list" style={{ maxHeight: '200px', overflowY: 'auto' }}>
              {exportModalResults.map((item, idx) => (
                <li
                  key={idx}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '8px',
                  }}
                >
                  <div>
                    <strong>{item.line_id}</strong> ({item.trace_count} traces,{' '}
                    {(item.size_bytes / 1024).toFixed(1)} KB)
                  </div>
                  <a
                    href={item.download_url}
                    download={item.filename}
                    className="btn-save-confirm"
                    style={{ textDecoration: 'none', padding: '4px 10px', fontSize: '0.8rem' }}
                  >
                    Tải về
                  </a>
                </li>
              ))}
            </ul>
            <div className="modal-actions">
              <button type="button" className="btn-cancel" onClick={() => setExportModalResults(null)}>
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL CONFIRM DELETE BLOCK FILE */}
      {showDeleteBlockModal && deleteBlockTarget && (
        <div className="modal-backdrop" onClick={() => setShowDeleteBlockModal(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Xóa File Lô Đã Xử Lý</h3>
            <p>
              Bạn có chắc chắn muốn xóa dữ liệu Lô địa chấn từ file{' '}
              <strong>{deleteBlockTarget.name}</strong> ({deleteBlockTarget.count} Lô)?
            </p>
            <div className="modal-actions">
              <button
                type="button"
                className="btn-cancel"
                onClick={() => {
                  setShowDeleteBlockModal(false)
                  setDeleteBlockTarget(null)
                }}
              >
                Hủy
              </button>
              <button
                type="button"
                className="btn-delete-confirm"
                disabled={deletingBlocks}
                onClick={handleConfirmDeleteBlockFile}
              >
                {deletingBlocks ? 'Đang xóa...' : 'Xóa file lô'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CRS CONFIGURATION & SELECTION MODAL */}
      <CrsConfigModal
        isOpen={showCrsModal}
        files={pendingSegyFiles}
        inspection={inspectionResult}
        inspecting={inspectingHeader}
        onClose={() => {
          setShowCrsModal(false)
          setPendingSegyFiles([])
          setInspectionResult(null)
        }}
        onConfirm={handleConfirmCrsUpload}
      />
    </main>
  )
}
