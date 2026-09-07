import { apiClient } from './client'
import type {
  GeoJSONFeatureCollection,
  SeismicBlock,
  BlockUploadResponse,
  BlockSplitRequest,
  UndoSplitResponse,
} from '../types/api'

export const blocksApi = {
  /**
   * Upload shapefile .zip to Backend 1 (segy-processing-service :8000 via proxy /api/blocks/upload-zip)
   */
  uploadZip: async (file: File): Promise<BlockUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)

    return apiClient<BlockUploadResponse>('/api/blocks/upload-zip', {
      method: 'POST',
      body: formData,
    })
  },

  /**
   * Get all blocks as GeoJSON FeatureCollection from Backend 2 (data-serving :8001 via proxy /api/blocks/geojson)
   */
  getGeoJSON: async (statusFilter = 'active'): Promise<GeoJSONFeatureCollection> => {
    return apiClient<GeoJSONFeatureCollection>(
      `/api/blocks/geojson?status_filter=${encodeURIComponent(statusFilter)}`
    )
  },

  /**
   * List blocks from Backend 2
   */
  listBlocks: async (statusFilter = 'active'): Promise<SeismicBlock[]> => {
    return apiClient<SeismicBlock[]>(
      `/api/blocks?status_filter=${encodeURIComponent(statusFilter)}`
    )
  },

  /**
   * Get detail of a specific block
   */
  getBlockDetail: async (blockId: number): Promise<SeismicBlock> => {
    return apiClient<SeismicBlock>(`/api/blocks/${blockId}`)
  },

  /**
   * Split a block using a WKT LineString cut-line
   */
  splitBlock: async (
    blockId: number,
    data: BlockSplitRequest
  ): Promise<SeismicBlock[]> => {
    return apiClient<SeismicBlock[]>(`/api/blocks/${blockId}/split`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
  },

  /**
   * Command Pattern Undo — hoàn tác thao tác tách lô gần nhất.
   * Xóa các lô con và phục hồi lô cha về trạng thái 'active'.
   */
  undoSplit: async (parentBlockId: number): Promise<UndoSplitResponse> => {
    return apiClient<UndoSplitResponse>('/api/blocks/undo-split', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ parent_block_id: parentBlockId }),
    })
  },
}
