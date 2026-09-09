import { useEffect, useRef, useState } from 'react'
import Map from 'ol/Map'
import View from 'ol/View'
import GeoJSON from 'ol/format/GeoJSON'
import TileLayer from 'ol/layer/Tile'
import VectorLayer from 'ol/layer/Vector'
import XYZ from 'ol/source/XYZ'
import VectorSource from 'ol/source/Vector'
import { Fill, Circle as CircleStyle, Stroke, Style } from 'ol/style'
import { fromLonLat, toLonLat } from 'ol/proj'
import Draw from 'ol/interaction/Draw'
import Feature from 'ol/Feature'
import LineString from 'ol/geom/LineString'
import Polygon from 'ol/geom/Polygon'
import MultiPolygon from 'ol/geom/MultiPolygon'
import { getCenter } from 'ol/extent'
import VectorTileLayer from 'ol/layer/VectorTile'
import VectorTileSource from 'ol/source/VectorTile'
import MVT from 'ol/format/MVT'
import { getSegyMvtTileUrlTemplate } from '../api/seismicApi'
import type { GeoJSONFeatureCollection, Geometry, LayerData } from '../types/api'
import { clipLineStringByPolygon, isPointInPolygon } from '../utils/geoClipping'

export type BlockClickInfo = {
  id: number
  block_code: string
  operator: string | null
  basin_name: string | null
  area_km2: number | null
  geometry: Geometry | null
  polygonRing: [number, number][]
  coordinate: [number, number]
  pixel: [number, number]
  intersectingLineCount: number
}

type Props = {
  data: LayerData | null
  blockData: GeoJSONFeatureCollection | null
  showLines: boolean
  showPoints: boolean
  showTraces: boolean
  showBlocks: boolean
  selectedBlockId: number | null
  isDrawingPolygon?: boolean
  drawnPolygonRing?: [number, number][] | null
  savedPolygonRings?: [number, number][][]
  onPolygonFinish?: (ring: [number, number][]) => void
  onBlockClick?: (info: BlockClickInfo | null) => void
  isSplittingBlock?: boolean
  splitLineCoords?: [number, number][] | null
  onSplitLineFinish?: (coords: [number, number][]) => void
  focusedBlock?: { code: string; timestamp: number } | null
  mvtFileIds?: number[]
}

type HoveredLine = {
  properties: Record<string, unknown>
  coordinate: [number, number]
  pixel: [number, number]
} | null

const format = new GeoJSON()

const defaultLineStyle = new Style({ stroke: new Stroke({ color: '#e4572e', width: 4 }) })
const defaultLineHoverStyle = new Style({ stroke: new Stroke({ color: '#172326', width: 7 }) })

const insideLineStyle = new Style({ stroke: new Stroke({ color: '#0284c7', width: 4 }) })
const insideLineHoverStyle = new Style({ stroke: new Stroke({ color: '#0369a1', width: 7 }) })

const outsideLineStyle = new Style({ stroke: new Stroke({ color: '#dc2626', width: 4 }) })
const outsideLineHoverStyle = new Style({ stroke: new Stroke({ color: '#991b1b', width: 7 }) })

const pointStyle = new Style({
  image: new CircleStyle({
    radius: 4,
    fill: new Fill({ color: '#1d7a8c' }),
  }),
})

const traceStyle = new Style({
  image: new CircleStyle({
    radius: 2.5,
    fill: new Fill({ color: '#f3a712' }),
  }),
})

const polygonStyle = new Style({
  stroke: new Stroke({
    color: 'rgba(23, 35, 38, 0.45)',
    width: 2,
    lineDash: [6, 6],
  }),
  fill: new Fill({
    color: 'rgba(23, 35, 38, 0.05)',
  }),
})

// Phong cách hiển thị Block Polygon: viền nét đứt xanh thẫm, nền trong suốt 10-15%
const blockNormalStyle = new Style({
  stroke: new Stroke({
    color: '#0284c7', // Xanh dương đậm
    width: 2,
    lineDash: [6, 4],
  }),
  fill: new Fill({
    color: 'rgba(2, 132, 199, 0.12)', // Trong suốt 12%
  }),
})

// Highlight Block được chọn: viền cam sáng
const blockSelectedStyle = new Style({
  stroke: new Stroke({
    color: '#f97316', // Cam sáng
    width: 3.5,
  }),
  fill: new Fill({
    color: 'rgba(249, 115, 22, 0.22)',
  }),
})

// Nét vẽ đường cắt lô (Split Line)
const splitLineStyle = new Style({
  stroke: new Stroke({
    color: '#ef4444', // Đỏ
    width: 3,
    lineDash: [8, 6],
  }),
})

function extractLineStrings(geometry: Geometry | null): [number, number][][] {
  if (!geometry) return []
  if (geometry.type === 'LineString') {
    return [geometry.coordinates as [number, number][]]
  }
  if (geometry.type === 'MultiLineString') {
    return geometry.coordinates as [number, number][][]
  }
  return []
}

function extractPolygonRingFromOlFeature(feature: Feature): [number, number][] {
  const geom = feature.getGeometry()
  if (!geom) return []
  const geom4326 = geom.clone().transform('EPSG:3857', 'EPSG:4326')
  const type = geom4326.getType()
  if (type === 'Polygon') {
    const polyGeom = geom4326 as Polygon
    const coords = polyGeom.getCoordinates()
    return (coords[0] || []) as [number, number][]
  }
  if (type === 'MultiPolygon') {
    const multiPolyGeom = geom4326 as MultiPolygon
    const coords = multiPolyGeom.getCoordinates()
    return (coords[0]?.[0] || []) as [number, number][]
  }
  return []
}

export function SeismicMap({
  data,
  blockData,
  showLines,
  showPoints,
  showTraces,
  showBlocks,
  selectedBlockId,
  isDrawingPolygon = false,
  drawnPolygonRing = null,
  savedPolygonRings = [],
  onPolygonFinish,
  onBlockClick,
  isSplittingBlock = false,
  splitLineCoords = null,
  onSplitLineFinish,
  focusedBlock = null,
  mvtFileIds = [],
}: Props) {
  const targetRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<Map | null>(null)
  const layersRef = useRef<{
    lines: VectorLayer<VectorSource>
    insideLines: VectorLayer<VectorSource>
    outsideLines: VectorLayer<VectorSource>
    polygon: VectorLayer<VectorSource>
    savedPolygons: VectorLayer<VectorSource>
    blocks: VectorLayer<VectorSource>
    splitLine: VectorLayer<VectorSource>
    points: VectorLayer<VectorSource>
    traces: VectorLayer<VectorSource>
    mvt: VectorTileLayer
  } | null>(null)
  const [hoveredLine, setHoveredLine] = useState<HoveredLine>(null)

  const onBlockClickRef = useRef(onBlockClick)
  useEffect(() => {
    onBlockClickRef.current = onBlockClick
  }, [onBlockClick])

  const dataRef = useRef(data)
  useEffect(() => {
    dataRef.current = data
  }, [data])

  const selectedBlockIdRef = useRef(selectedBlockId)
  useEffect(() => {
    selectedBlockIdRef.current = selectedBlockId
    if (layersRef.current?.blocks) {
      layersRef.current.blocks.changed()
    }
  }, [selectedBlockId])

  const showLinesRef = useRef(showLines)
  const showPointsRef = useRef(showPoints)
  const showTracesRef = useRef(showTraces)

  useEffect(() => { showLinesRef.current = showLines }, [showLines])
  useEffect(() => { showPointsRef.current = showPoints }, [showPoints])
  useEffect(() => { showTracesRef.current = showTraces }, [showTraces])

  useEffect(() => {
    if (layersRef.current?.mvt) {
      layersRef.current.mvt.changed()
    }
  }, [showLines, showPoints, showTraces])

  const fittedDataKeyRef = useRef<string | null>(null)

  useEffect(() => {
    if (!targetRef.current) return

    const lines = new VectorLayer({
      source: new VectorSource(),
      style: (feature) => (feature.get('hovered') ? defaultLineHoverStyle : defaultLineStyle),
    })

    const insideLines = new VectorLayer({
      source: new VectorSource(),
      style: (feature) => (feature.get('hovered') ? insideLineHoverStyle : insideLineStyle),
    })

    const outsideLines = new VectorLayer({
      source: new VectorSource(),
      style: (feature) => (feature.get('hovered') ? outsideLineHoverStyle : outsideLineStyle),
    })

    const polygonLayer = new VectorLayer({
      source: new VectorSource(),
      style: polygonStyle,
    })

    const savedPolygonsLayer = new VectorLayer({
      source: new VectorSource(),
      style: polygonStyle,
    })

    const blocksLayer = new VectorLayer({
      source: new VectorSource(),
      style: (feature) => {
        const isSelected = feature.get('id') === selectedBlockIdRef.current
        return isSelected ? blockSelectedStyle : blockNormalStyle
      },
    })

    const splitLineLayer = new VectorLayer({
      source: new VectorSource(),
      style: splitLineStyle,
    })

    const points = new VectorLayer({ source: new VectorSource(), style: pointStyle })
    const traces = new VectorLayer({ source: new VectorSource(), style: traceStyle })

    const mvtLayer = new VectorTileLayer({
      source: new VectorTileSource({
        format: new MVT(),
        url: getSegyMvtTileUrlTemplate(mvtFileIds),
      }),
      visible: Boolean(mvtFileIds && mvtFileIds.length > 0),
      style: (feature) => {
        const layerName = feature.get('layer')
        if (layerName === 'traces') return showTracesRef.current ? traceStyle : undefined
        if (layerName === 'shot_points') return showPointsRef.current ? pointStyle : undefined
        if (layerName === 'lines') return showLinesRef.current ? defaultLineStyle : undefined
        return undefined
      },
    })

    const map = new Map({
      target: targetRef.current,
      layers: [
        new TileLayer({
          source: new XYZ({
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
            attributions:
              'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), and the GIS User Community',
            maxZoom: 19,
          }),
        }),
        blocksLayer,
        mvtLayer,
        lines,
        insideLines,
        outsideLines,
        savedPolygonsLayer,
        polygonLayer,
        splitLineLayer,
        points,
        traces,
      ],
      view: new View({ center: fromLonLat([106.7, 10.78]), zoom: 11 }),
    })

    mapRef.current = map
    layersRef.current = {
      lines,
      insideLines,
      outsideLines,
      polygon: polygonLayer,
      savedPolygons: savedPolygonsLayer,
      blocks: blocksLayer,
      splitLine: splitLineLayer,
      points,
      traces,
      mvt: mvtLayer,
    }

    // Pointer move handler for line tooltip
    map.on('pointermove', (event) => {
      if (event.dragging) return

      // Do not show line tooltip if drawing or splitting
      const targetEl = map.getTargetElement()
      if (targetEl.classList.contains('is-drawing') || targetEl.classList.contains('is-splitting')) {
        return
      }

      const targetLayers = [lines, insideLines, outsideLines]
      const hit = map.forEachFeatureAtPixel(
        event.pixel,
        (feature, layer) => (targetLayers.includes(layer as any) ? feature : undefined),
        { hitTolerance: 7 }
      )

      targetLayers.forEach((layer) => {
        layer.getSource()?.getFeatures().forEach((feature) => {
          feature.set('hovered', feature === hit)
        })
        layer.changed()
      })

      if (!hit) {
        setHoveredLine(null)
        targetEl.style.cursor = ''
        return
      }

      const properties = hit.getProperties()
      setHoveredLine({
        properties,
        coordinate: toLonLat(event.coordinate) as [number, number],
        pixel: event.pixel as [number, number],
      })
      targetEl.style.cursor = 'pointer'
    })

    // Click handler for Block selection & Popup
    map.on('singleclick', (event) => {
      const targetEl = map.getTargetElement()
      if (targetEl.classList.contains('is-drawing') || targetEl.classList.contains('is-splitting')) {
        return
      }

      const hitFeature = map.forEachFeatureAtPixel(
        event.pixel,
        (feature, layer) => (layer === blocksLayer ? feature : undefined),
        { hitTolerance: 5 }
      )

      if (hitFeature && onBlockClickRef.current) {
        const props = hitFeature.getProperties()
        const clickLonLat = toLonLat(event.coordinate) as [number, number]
        const ring = extractPolygonRingFromOlFeature(hitFeature as Feature)

        // Calculate intersecting lines count
        let intersectingCount = 0
        const currentData = dataRef.current
        if (currentData?.lines && ring.length >= 3) {
          for (const lineFeat of currentData.lines.features) {
            const lineStrings = extractLineStrings(lineFeat.geometry)
            let intersects = false
            for (const segCoords of lineStrings) {
              for (const pt of segCoords) {
                if (isPointInPolygon(pt, ring)) {
                  intersects = true
                  break
                }
              }
              if (intersects) break
            }
            if (intersects) intersectingCount++
          }
        }

        onBlockClickRef.current({
          id: props.id as number,
          block_code: (props.block_code as string) || `Block_${props.id}`,
          operator: (props.operator as string) || null,
          basin_name: (props.basin_name as string) || null,
          area_km2: (props.area_km2 as number) || null,
          geometry: (props.geometry as Geometry) || null,
          polygonRing: ring,
          coordinate: clickLonLat,
          pixel: event.pixel as [number, number],
          intersectingLineCount: intersectingCount,
        })
      } else if (!hitFeature && onBlockClickRef.current) {
        onBlockClickRef.current(null)
      }
    })

    return () => {
      map.setTarget(undefined)
      mapRef.current = null
    }
  }, [])

  // Handle Polygon Drawing Interaction
  useEffect(() => {
    const map = mapRef.current
    const layerSet = layersRef.current
    if (!map || !layerSet) return

    const targetEl = map.getTargetElement()
    if (!isDrawingPolygon) {
      targetEl.classList.remove('is-drawing')
      if (!isSplittingBlock) targetEl.style.cursor = ''
      return
    }

    targetEl.classList.add('is-drawing')
    targetEl.style.cursor = 'crosshair'

    const drawSource = layerSet.polygon.getSource()
    if (!drawSource) return

    const drawInteraction = new Draw({
      source: drawSource,
      type: 'Polygon',
      style: polygonStyle,
    })

    drawInteraction.on('drawend', (event) => {
      const geometry = event.feature.getGeometry() as Polygon
      if (geometry) {
        const transformedGeom = geometry.clone().transform('EPSG:3857', 'EPSG:4326') as Polygon
        const ring = transformedGeom.getCoordinates()[0] as [number, number][]
        if (onPolygonFinish && ring && ring.length >= 3) {
          onPolygonFinish(ring)
        }
      }
    })

    map.addInteraction(drawInteraction)

    return () => {
      map.removeInteraction(drawInteraction)
      targetEl.classList.remove('is-drawing')
    }
  }, [isDrawingPolygon, isSplittingBlock, onPolygonFinish])

  // Handle Split Line Drawing Interaction (2 clicks to draw a cut line across block)
  useEffect(() => {
    const map = mapRef.current
    const layerSet = layersRef.current
    if (!map || !layerSet) return

    const targetEl = map.getTargetElement()
    if (!isSplittingBlock) {
      targetEl.classList.remove('is-splitting')
      if (!isDrawingPolygon) targetEl.style.cursor = ''
      return
    }

    targetEl.classList.add('is-splitting')
    targetEl.style.cursor = 'crosshair'

    const splitSource = layerSet.splitLine.getSource()
    if (!splitSource) return

    const drawLineInteraction = new Draw({
      source: splitSource,
      type: 'LineString',
      maxPoints: 2, // Exactly 2 points for a straight cut line
      style: splitLineStyle,
    })

    drawLineInteraction.on('drawend', (event) => {
      const geometry = event.feature.getGeometry() as LineString
      if (geometry) {
        const transformedGeom = geometry.clone().transform('EPSG:3857', 'EPSG:4326') as LineString
        const coords = transformedGeom.getCoordinates() as [number, number][]
        if (onSplitLineFinish && coords.length === 2) {
          onSplitLineFinish(coords)
        }
      }
    })

    map.addInteraction(drawLineInteraction)

    return () => {
      map.removeInteraction(drawLineInteraction)
      targetEl.classList.remove('is-splitting')
    }
  }, [isSplittingBlock, isDrawingPolygon, onSplitLineFinish])

  // Render Split Line (drawn by user or passed via props)
  useEffect(() => {
    const layerSet = layersRef.current
    if (!layerSet) return
    const splitSource = layerSet.splitLine.getSource()
    splitSource?.clear()

    if (splitLineCoords && splitLineCoords.length === 2) {
      const lineGeom = new LineString(splitLineCoords).transform('EPSG:4326', 'EPSG:3857')
      splitSource?.addFeature(new Feature({ geometry: lineGeom }))
    }
  }, [splitLineCoords])

  // Render Blocks layer
  useEffect(() => {
    const layerSet = layersRef.current
    if (!layerSet) return

    const blocksSource = layerSet.blocks.getSource()
    blocksSource?.clear()
    layerSet.blocks.setVisible(showBlocks)

    if (blockData && showBlocks) {
      const features = format.readFeatures(blockData, {
        dataProjection: 'EPSG:4326',
        featureProjection: 'EPSG:3857',
      })
      blocksSource?.addFeatures(features)
    }
  }, [blockData, showBlocks])

  // Render Polygon Geometry and Line Spatial Classification
  useEffect(() => {
    const layerSet = layersRef.current
    if (!layerSet) return

    // Drawn polygon
    const polySource = layerSet.polygon.getSource()
    polySource?.clear()
    if (drawnPolygonRing && drawnPolygonRing.length >= 3) {
      const polyGeom = new Polygon([drawnPolygonRing]).transform('EPSG:4326', 'EPSG:3857')
      polySource?.addFeature(new Feature({ geometry: polyGeom }))
    }

    // Saved polygons
    const savedPolySource = layerSet.savedPolygons.getSource()
    savedPolySource?.clear()
    for (const ring of savedPolygonRings) {
      if (ring.length >= 3) {
        const polyGeom = new Polygon([ring]).transform('EPSG:4326', 'EPSG:3857')
        savedPolySource?.addFeature(new Feature({ geometry: polyGeom }))
      }
    }

    const allActiveRings: [number, number][][] = [
      ...(drawnPolygonRing && drawnPolygonRing.length >= 3 ? [drawnPolygonRing] : []),
      ...savedPolygonRings.filter((r) => r.length >= 3),
    ]
    const hasPolygon = allActiveRings.length > 0

    const allActiveRings3857: [number, number][][] = allActiveRings.map((ring) =>
      ring.map((pt) => fromLonLat(pt) as [number, number])
    )

    const insideSource = layerSet.insideLines.getSource()
    const outsideSource = layerSet.outsideLines.getSource()
    const linesSource = layerSet.lines.getSource()

    if (hasPolygon && showLines && data?.lines?.features && data.lines.features.length > 0) {
      setTimeout(() => {
        if (!layersRef.current) return
        const inSrc = layersRef.current.insideLines.getSource()
        const outSrc = layersRef.current.outsideLines.getSource()
        inSrc?.clear()
        outSrc?.clear()

        const insideFeatures: Feature[] = []
        const outsideFeatures: Feature[] = []

        for (const feature of data.lines.features) {
          const geom = feature.geometry
          if (!geom) continue

          const lineCoordLists: [number, number][][] =
            geom.type === 'LineString'
              ? [(geom.coordinates as [number, number][]).map((pt) => fromLonLat(pt) as [number, number])]
              : geom.type === 'MultiLineString'
              ? (geom.coordinates as [number, number][][]).map((list) =>
                  list.map((pt) => fromLonLat(pt) as [number, number])
                )
              : []

          for (const coords of lineCoordLists) {
            if (coords.length < 2) continue

            let outsidePaths: [number, number][][] = [coords]
            let insidePaths: [number, number][][] = []

            for (const ring3857 of allActiveRings3857) {
              const nextOutsidePaths: [number, number][][] = []
              for (const path of outsidePaths) {
                const { inside, outside } = clipLineStringByPolygon(path, ring3857)
                insidePaths.push(...inside)
                nextOutsidePaths.push(...outside)
              }
              outsidePaths = nextOutsidePaths
            }

            for (const inPath of insidePaths) {
              if (inPath.length >= 2) {
                const lineGeom = new LineString(inPath)
                const f = new Feature({ geometry: lineGeom })
                if (feature.properties) f.setProperties(feature.properties)
                insideFeatures.push(f)
              }
            }

            for (const outPath of outsidePaths) {
              if (outPath.length >= 2) {
                const lineGeom = new LineString(outPath)
                const f = new Feature({ geometry: lineGeom })
                if (feature.properties) f.setProperties(feature.properties)
                outsideFeatures.push(f)
              }
            }
          }
        }

        inSrc?.addFeatures(insideFeatures)
        outSrc?.addFeatures(outsideFeatures)

        layersRef.current.insideLines.setVisible(true)
        layersRef.current.outsideLines.setVisible(true)
        layersRef.current.lines.setVisible(false)
        layersRef.current.mvt.setVisible(false)
      }, 0)
    } else {
      insideSource?.clear()
      outsideSource?.clear()
      linesSource?.clear()

      layerSet.insideLines.setVisible(false)
      layerSet.outsideLines.setVisible(false)
      layerSet.lines.setVisible(!mvtFileIds?.length && showLines)
      layerSet.mvt.setVisible(Boolean(mvtFileIds && mvtFileIds.length > 0))

      if (data?.lines && showLines && !mvtFileIds?.length) {
        const features = format.readFeatures(data.lines, {
          dataProjection: 'EPSG:4326',
          featureProjection: 'EPSG:3857',
        })
        linesSource?.addFeatures(features)
      }
    }

    // Update point and trace layers
    const entries = [
      ['points', data?.shotPoints, layerSet.points, showPoints],
      ['traces', data?.traces, layerSet.traces, showTraces],
    ] as const

    let extent: [number, number, number, number] | null = null

    if (data?.lines && showLines) {
      const lineFeatures = format.readFeatures(data.lines, {
        dataProjection: 'EPSG:4326',
        featureProjection: 'EPSG:3857',
      })
      const tempSource = new VectorSource({ features: lineFeatures })
      const lineExtent = tempSource.getExtent()
      if (lineExtent && lineExtent.every(Number.isFinite)) {
        extent = lineExtent as [number, number, number, number]
      }
    }

    const hasMvt = Boolean(mvtFileIds && mvtFileIds.length > 0)

    entries.forEach(([, collection, layer, visible]) => {
      const source = layer.getSource()
      source?.clear()
      if (hasMvt) {
        layer.setVisible(false)
        return
      }
      layer.setVisible(visible)
      if (!collection || !visible) return

      const features = format.readFeatures(collection, {
        dataProjection: 'EPSG:4326',
        featureProjection: 'EPSG:3857',
      })
      source?.addFeatures(features)

      const nextExtent = source?.getExtent()
      if (nextExtent && nextExtent.every(Number.isFinite)) {
        const normalizedExtent = nextExtent as [number, number, number, number]
        extent = extent
          ? [
            Math.min(extent[0], normalizedExtent[0]),
            Math.min(extent[1], normalizedExtent[1]),
            Math.max(extent[2], normalizedExtent[2]),
            Math.max(extent[3], normalizedExtent[3]),
          ]
          : normalizedExtent
      }
    })

    const dataKey = `${data?.lines?.features.length ?? 0}_${data?.shotPoints?.features.length ?? 0}_${blockData?.features.length ?? 0}`
    if (extent && mapRef.current && fittedDataKeyRef.current !== dataKey) {
      fittedDataKeyRef.current = dataKey
      mapRef.current.getView().fit(extent, {
        padding: [60, 60, 60, 60],
        maxZoom: 15,
        duration: 500,
      })
    } else if (!data?.lines && blockData && showBlocks && mapRef.current && fittedDataKeyRef.current !== dataKey) {
      const blocksSource = layerSet.blocks.getSource()
      const bExtent = blocksSource?.getExtent()
      if (bExtent && bExtent.every(Number.isFinite)) {
        fittedDataKeyRef.current = dataKey
        mapRef.current.getView().fit(bExtent as [number, number, number, number], {
          padding: [60, 60, 60, 60],
          maxZoom: 14,
          duration: 500,
        })
      }
    }
  }, [data, blockData, showLines, showPoints, showTraces, showBlocks, drawnPolygonRing, savedPolygonRings])

  // Update MVT Vector Tile Source when mvtFileIds changes
  useEffect(() => {
    const layerSet = layersRef.current
    if (!layerSet?.mvt) return
    if (mvtFileIds && mvtFileIds.length > 0) {
      layerSet.mvt.setSource(
        new VectorTileSource({
          format: new MVT(),
          url: getSegyMvtTileUrlTemplate(mvtFileIds),
        })
      )
      layerSet.mvt.setVisible(true)
    } else {
      layerSet.mvt.setVisible(false)
    }
  }, [mvtFileIds])

  // Focus & Zoom to searched block feature
  useEffect(() => {
    if (!focusedBlock?.code || !mapRef.current || !layersRef.current?.blocks) return
    const blocksSource = layersRef.current.blocks.getSource()
    if (!blocksSource) return

    const targetCode = focusedBlock.code.trim().toLowerCase()
    const feat = blocksSource.getFeatures().find((f) => {
      const code = f.get('block_code')
      return code && code.toString().toLowerCase() === targetCode
    })

    if (feat && onBlockClickRef.current) {
      const geom = feat.getGeometry()
      if (geom) {
        const extent = geom.getExtent()
        mapRef.current.getView().fit(extent, {
          padding: [100, 100, 100, 100],
          maxZoom: 13,
          duration: 500,
        })

        const center3857 = getCenter(extent)
        const pixel = mapRef.current.getPixelFromCoordinate(center3857) || [window.innerWidth / 2, window.innerHeight / 2]
        const clickLonLat = toLonLat(center3857) as [number, number]
        const ring = extractPolygonRingFromOlFeature(feat)

        const props = feat.getProperties()

        // Calculate intersecting lines count
        let intersectingCount = 0
        const currentData = dataRef.current
        if (currentData?.lines && ring.length >= 3) {
          for (const lineFeat of currentData.lines.features) {
            const lineStrings = extractLineStrings(lineFeat.geometry)
            let intersects = false
            for (const segCoords of lineStrings) {
              for (const pt of segCoords) {
                if (isPointInPolygon(pt, ring)) {
                  intersects = true
                  break
                }
              }
              if (intersects) break
            }
            if (intersects) intersectingCount++
          }
        }

        onBlockClickRef.current({
          id: props.id as number,
          block_code: (props.block_code as string) || `Block_${props.id}`,
          operator: (props.operator as string) || null,
          basin_name: (props.basin_name as string) || null,
          area_km2: (props.area_km2 as number) || null,
          geometry: (props.geometry as Geometry) || null,
          polygonRing: ring,
          coordinate: clickLonLat,
          pixel: pixel as [number, number],
          intersectingLineCount: intersectingCount,
        })
      }
    }
  }, [focusedBlock?.timestamp])

  return (
    <div ref={targetRef} className="map" aria-label="Bản đồ dữ liệu địa chấn">
      {hoveredLine && (
        <div
          className="line-tooltip"
          style={{ left: hoveredLine.pixel[0] + 16, top: hoveredLine.pixel[1] + 16 }}
        >
          <span className="tooltip-kicker">SEISMIC LINE</span>
          <strong>{String(hoveredLine.properties.line_id ?? hoveredLine.properties.id)}</strong>
          <div className="tooltip-grid">
            <span>
              Longitude <b>{hoveredLine.coordinate[0].toFixed(6)}</b>
            </span>
            <span>
              Latitude <b>{hoveredLine.coordinate[1].toFixed(6)}</b>
            </span>
            <span>
              Traces <b>{String(hoveredLine.properties.trace_count ?? 0)}</b>
            </span>
            <span>
              Shot points <b>{String(hoveredLine.properties.shot_point_count ?? 0)}</b>
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
