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
import type { LayerData } from '../types/api'

type Props = { data: LayerData | null; showLines: boolean; showPoints: boolean; showTraces: boolean }
type HoveredLine = { properties: Record<string, unknown>; coordinate: [number, number]; pixel: [number, number] } | null

const format = new GeoJSON()
const lineStyle = new Style({ stroke: new Stroke({ color: '#e4572e', width: 4 }) })
const lineHoverStyle = new Style({ stroke: new Stroke({ color: '#172326', width: 7 }) })
const pointStyle = new Style({ image: new CircleStyle({ radius: 5, fill: new Fill({ color: '#1d7a8c' }), stroke: new Stroke({ color: '#fff', width: 1.5 }) }) })
const traceStyle = new Style({ image: new CircleStyle({ radius: 3, fill: new Fill({ color: '#f3a712' }), stroke: new Stroke({ color: '#fff', width: 1 }) }) })

export function SeismicMap({ data, showLines, showPoints, showTraces }: Props) {
  const targetRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<Map | null>(null)
  const layersRef = useRef<{ lines: VectorLayer<VectorSource>; points: VectorLayer<VectorSource>; traces: VectorLayer<VectorSource> } | null>(null)
  const [hoveredLine, setHoveredLine] = useState<HoveredLine>(null)

  useEffect(() => {
    if (!targetRef.current) return
    const lines = new VectorLayer({
      source: new VectorSource(),
      style: (feature) => feature.get('hovered') ? lineHoverStyle : lineStyle,
    })
    const points = new VectorLayer({ source: new VectorSource(), style: pointStyle })
    const traces = new VectorLayer({ source: new VectorSource(), style: traceStyle })
    const map = new Map({
      target: targetRef.current,
      layers: [new TileLayer({ source: new OSM() }), lines, points, traces],
      view: new View({ center: fromLonLat([106.7, 10.78]), zoom: 11 }),
    })
    mapRef.current = map
    layersRef.current = { lines, points, traces }
    map.on('pointermove', (event) => {
      if (event.dragging) return
      const hit = map.forEachFeatureAtPixel(
        event.pixel,
        (feature, layer) => layer === lines ? feature : undefined,
        { hitTolerance: 7 },
      )
      const source = lines.getSource()
      source?.getFeatures().forEach((feature) => feature.set('hovered', feature === hit))
      lines.changed()
      if (!hit) {
        setHoveredLine(null)
        map.getTargetElement().style.cursor = ''
        return
      }
      const properties = hit.getProperties()
      setHoveredLine({
        properties,
        coordinate: toLonLat(event.coordinate) as [number, number],
        pixel: event.pixel as [number, number],
      })
      map.getTargetElement().style.cursor = 'pointer'
    })
    return () => {
      map.setTarget(undefined)
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    const layerSet = layersRef.current
    if (!layerSet) return
    const entries = [
      ['lines', data?.lines, layerSet.lines, showLines],
      ['points', data?.shotPoints, layerSet.points, showPoints],
      ['traces', data?.traces, layerSet.traces, showTraces],
    ] as const
    let extent: [number, number, number, number] | null = null
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
    if (extent && mapRef.current) mapRef.current.getView().fit(extent, { padding: [60, 60, 60, 60], maxZoom: 15, duration: 500 })
  }, [data, showLines, showPoints, showTraces])

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
