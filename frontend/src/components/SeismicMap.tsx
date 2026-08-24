import { useEffect, useRef, useState } from 'react'
import Map from 'ol/Map'
import View from 'ol/View'
import GeoJSON from 'ol/format/GeoJSON'
import TileLayer from 'ol/layer/Tile'
import VectorLayer from 'ol/layer/Vector'
import OSM from 'ol/source/OSM'
import VectorSource from 'ol/source/Vector'
import { Fill, Circle as CircleStyle, Stroke, Style } from 'ol/style'
import { fromLonLat, toLonLat } from 'ol/proj'
import Draw from 'ol/interaction/Draw'
import Feature from 'ol/Feature'
import LineString from 'ol/geom/LineString'
import Polygon from 'ol/geom/Polygon'
import type { Geometry, LayerData } from '../types/api'
import { clipLineStringByPolygon } from '../utils/geoClipping'

type Props = {
  data: LayerData | null
  showLines: boolean
  showPoints: boolean
  showTraces: boolean
  isDrawingPolygon?: boolean
  drawnPolygonRing?: [number, number][] | null
  onPolygonFinish?: (ring: [number, number][]) => void
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
    radius: 5,
    fill: new Fill({ color: '#1d7a8c' }),
    stroke: new Stroke({ color: '#fff', width: 1.5 }),
  }),
})

const traceStyle = new Style({
  image: new CircleStyle({
    radius: 3,
    fill: new Fill({ color: '#f3a712' }),
    stroke: new Stroke({ color: '#fff', width: 1 }),
  }),
})

const polygonStyle = new Style({
  stroke: new Stroke({
    color: 'rgba(23, 35, 38, 0.45)', // Nét đứt mờ hơn theo yêu cầu
    width: 2,
    lineDash: [6, 6],
  }),
  fill: new Fill({
    color: 'rgba(23, 35, 38, 0.05)',
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

export function SeismicMap({
  data,
  showLines,
  showPoints,
  showTraces,
  isDrawingPolygon = false,
  drawnPolygonRing = null,
  onPolygonFinish,
}: Props) {
  const targetRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<Map | null>(null)
  const layersRef = useRef<{
    lines: VectorLayer<VectorSource>
    insideLines: VectorLayer<VectorSource>
    outsideLines: VectorLayer<VectorSource>
    polygon: VectorLayer<VectorSource>
    points: VectorLayer<VectorSource>
    traces: VectorLayer<VectorSource>
  } | null>(null)
  const [hoveredLine, setHoveredLine] = useState<HoveredLine>(null)

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

    const points = new VectorLayer({ source: new VectorSource(), style: pointStyle })
    const traces = new VectorLayer({ source: new VectorSource(), style: traceStyle })

    const map = new Map({
      target: targetRef.current,
      layers: [
        new TileLayer({ source: new OSM() }),
        lines,
        insideLines,
        outsideLines,
        polygonLayer,
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
      points,
      traces,
    }

    map.on('pointermove', (event) => {
      if (event.dragging) return
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
        if (!map.getTargetElement().classList.contains('is-drawing')) {
          map.getTargetElement().style.cursor = ''
        }
        return
      }

      const properties = hit.getProperties()
      setHoveredLine({
        properties,
        coordinate: toLonLat(event.coordinate) as [number, number],
        pixel: event.pixel as [number, number],
      })
      if (!map.getTargetElement().classList.contains('is-drawing')) {
        map.getTargetElement().style.cursor = 'pointer'
      }
    })

    return () => {
      map.setTarget(undefined)
      mapRef.current = null
    }
  }, [])

  // Handle polygon drawing interaction
  useEffect(() => {
    const map = mapRef.current
    const layerSet = layersRef.current
    if (!map || !layerSet) return

    const targetEl = map.getTargetElement()
    if (!isDrawingPolygon) {
      targetEl.classList.remove('is-drawing')
      targetEl.style.cursor = ''
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
  }, [isDrawingPolygon, onPolygonFinish])

  // Handle polygon geometry rendering and line spatial classification
  useEffect(() => {
    const layerSet = layersRef.current
    if (!layerSet) return

    const polySource = layerSet.polygon.getSource()
    polySource?.clear()

    if (drawnPolygonRing && drawnPolygonRing.length >= 3) {
      const polyGeom = new Polygon([drawnPolygonRing]).transform('EPSG:4326', 'EPSG:3857')
      polySource?.addFeature(new Feature({ geometry: polyGeom }))
    }

    const insideSource = layerSet.insideLines.getSource()
    const outsideSource = layerSet.outsideLines.getSource()
    const linesSource = layerSet.lines.getSource()

    insideSource?.clear()
    outsideSource?.clear()
    linesSource?.clear()

    const hasPolygon = Boolean(drawnPolygonRing && drawnPolygonRing.length >= 3)

    if (hasPolygon && data?.lines && showLines) {
      layerSet.lines.setVisible(false)
      layerSet.insideLines.setVisible(true)
      layerSet.outsideLines.setVisible(true)

      for (const feature of data.lines.features) {
        const lineStrings = extractLineStrings(feature.geometry)
        for (const lineCoords of lineStrings) {
          // Project coordinates to EPSG:3857 before spatial clipping to avoid curvature distortion
          const lineCoords3857 = lineCoords.map((c) => fromLonLat(c) as [number, number])
          const polyRing3857 = drawnPolygonRing!.map((c) => fromLonLat(c) as [number, number])

          const { inside, outside } = clipLineStringByPolygon(lineCoords3857, polyRing3857)

          for (const subCoords of inside) {
            const geom = new LineString(subCoords)
            const f = new Feature({ geometry: geom })
            f.setProperties(feature.properties)
            insideSource?.addFeature(f)
          }

          for (const subCoords of outside) {
            const geom = new LineString(subCoords)
            const f = new Feature({ geometry: geom })
            f.setProperties(feature.properties)
            outsideSource?.addFeature(f)
          }
        }
      }
    } else {
      layerSet.lines.setVisible(showLines)
      layerSet.insideLines.setVisible(false)
      layerSet.outsideLines.setVisible(false)

      if (data?.lines && showLines) {
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

    entries.forEach(([, collection, layer, visible]) => {
      const source = layer.getSource()
      source?.clear()
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

    if (extent && mapRef.current) {
      mapRef.current.getView().fit(extent, {
        padding: [60, 60, 60, 60],
        maxZoom: 15,
        duration: 500,
      })
    }
  }, [data, showLines, showPoints, showTraces, drawnPolygonRing])

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
            <span>Longitude <b>{hoveredLine.coordinate[0].toFixed(6)}</b></span>
            <span>Latitude <b>{hoveredLine.coordinate[1].toFixed(6)}</b></span>
            <span>Traces <b>{String(hoveredLine.properties.trace_count ?? 0)}</b></span>
            <span>Shot points <b>{String(hoveredLine.properties.shot_point_count ?? 0)}</b></span>
          </div>
        </div>
      )}
    </div>
  )
}

