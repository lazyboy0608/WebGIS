/**
 * Utility functions for exact spatial geometry operations:
 * - Point-in-Polygon test using clean Even-Odd Ray Casting
 * - Exact 2D Segment-polygon edge intersection calculations
 * - Line clipping and classification into inside (blue) and outside (red) paths.
 */

export function isPointInPolygon(
  point: [number, number],
  polygon: [number, number][]
): boolean {
  if (!polygon || polygon.length < 3) return false

  const [px, py] = point
  let inside = false

  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i]
    const [xj, yj] = polygon[j]

    const intersect =
      yi > py !== yj > py &&
      px < ((xj - xi) * (py - yi)) / (yj - yi) + xi
    if (intersect) inside = !inside
  }

  return inside
}

interface IntersectionResult {
  point: [number, number]
  t: number
}

function getSegmentIntersection(
  p1: [number, number],
  p2: [number, number],
  p3: [number, number],
  p4: [number, number]
): IntersectionResult | null {
  const [x1, y1] = p1
  const [x2, y2] = p2
  const [x3, y3] = p3
  const [x4, y4] = p4

  const rx = x2 - x1
  const ry = y2 - y1
  const sx = x4 - x3
  const sy = y4 - y3

  const denom = rx * sy - ry * sx
  if (Math.abs(denom) < 1e-12) return null // Parallel or collinear

  const qx = x3 - x1
  const qy = y3 - y1

  const t = (qx * sy - qy * sx) / denom
  const u = (qx * ry - qy * rx) / denom

  const eps = 1e-9
  if (t >= -eps && t <= 1 + eps && u >= -eps && u <= 1 + eps) {
    const tClamped = Math.max(0, Math.min(1, t))
    const ix = x1 + tClamped * rx
    const iy = y1 + tClamped * ry
    return { point: [ix, iy], t: tClamped }
  }

  return null
}

/**
 * Clips a single LineString (array of [x, y] coordinates) against a closed polygon ring.
 * Returns exact inside sub-lines and outside sub-lines meeting at exact boundary intersection points.
 */
export function clipLineStringByPolygon(
  lineCoordinates: [number, number][],
  polygonRing: [number, number][]
): { inside: [number, number][][]; outside: [number, number][][] } {
  if (lineCoordinates.length < 2 || polygonRing.length < 3) {
    return { inside: [], outside: [lineCoordinates] }
  }

  // Ensure polygon ring is closed for edge traversal
  const poly = [...polygonRing]
  const first = poly[0]
  const last = poly[poly.length - 1]
  if (first[0] !== last[0] || first[1] !== last[1]) {
    poly.push(first)
  }

  const insideLines: [number, number][][] = []
  const outsideLines: [number, number][][] = []

  let currentInsidePath: [number, number][] = []
  let currentOutsidePath: [number, number][] = []

  const addSegmentToPaths = (
    startPt: [number, number],
    endPt: [number, number],
    isInside: boolean
  ) => {
    // Skip tiny zero-length sub-segments
    if (Math.hypot(endPt[0] - startPt[0], endPt[1] - startPt[1]) < 1e-7) {
      return
    }

    if (isInside) {
      // Flush outside path if active
      if (currentOutsidePath.length >= 2) {
        outsideLines.push(currentOutsidePath)
      }
      currentOutsidePath = []

      // Append to inside path
      if (currentInsidePath.length === 0) {
        currentInsidePath.push(startPt)
      } else {
        const lastPt = currentInsidePath[currentInsidePath.length - 1]
        if (Math.hypot(startPt[0] - lastPt[0], startPt[1] - lastPt[1]) > 1e-7) {
          currentInsidePath.push(startPt)
        }
      }
      currentInsidePath.push(endPt)
    } else {
      // Flush inside path if active
      if (currentInsidePath.length >= 2) {
        insideLines.push(currentInsidePath)
      }
      currentInsidePath = []

      // Append to outside path
      if (currentOutsidePath.length === 0) {
        currentOutsidePath.push(startPt)
      } else {
        const lastPt = currentOutsidePath[currentOutsidePath.length - 1]
        if (Math.hypot(startPt[0] - lastPt[0], startPt[1] - lastPt[1]) > 1e-7) {
          currentOutsidePath.push(startPt)
        }
      }
      currentOutsidePath.push(endPt)
    }
  }

  for (let i = 0; i < lineCoordinates.length - 1; i++) {
    const p1 = lineCoordinates[i]
    const p2 = lineCoordinates[i + 1]

    // Find all intersections along segment p1 -> p2
    const intersections: IntersectionResult[] = []
    for (let j = 0; j < poly.length - 1; j++) {
      const v1 = poly[j]
      const v2 = poly[j + 1]
      const inter = getSegmentIntersection(p1, p2, v1, v2)
      if (inter) {
        intersections.push(inter)
      }
    }

    // Sort intersections in ascending order of parameter t along p1 -> p2
    intersections.sort((a, b) => a.t - b.t)

    // Collect split points along segment p1 -> p2
    const pts: [number, number][] = [p1]

    for (const inter of intersections) {
      const lastPt = pts[pts.length - 1]
      if (Math.hypot(inter.point[0] - lastPt[0], inter.point[1] - lastPt[1]) > 1e-7) {
        pts.push(inter.point)
      }
    }
    const lastPt = pts[pts.length - 1]
    if (Math.hypot(p2[0] - lastPt[0], p2[1] - lastPt[1]) > 1e-7) {
      pts.push(p2)
    }

    // Process each sub-interval
    for (let k = 0; k < pts.length - 1; k++) {
      const startPt = pts[k]
      const endPt = pts[k + 1]
      const midPt: [number, number] = [
        (startPt[0] + endPt[0]) / 2,
        (startPt[1] + endPt[1]) / 2,
      ]

      const inside = isPointInPolygon(midPt, poly)
      addSegmentToPaths(startPt, endPt, inside)
    }
  }

  // Final flush
  if (currentInsidePath.length >= 2) insideLines.push(currentInsidePath)
  if (currentOutsidePath.length >= 2) outsideLines.push(currentOutsidePath)

  return { inside: insideLines, outside: outsideLines }
}
