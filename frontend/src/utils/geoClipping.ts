/**
 * Utility functions for exact spatial geometry operations:
 * - Point-in-Polygon test combining Non-Zero Winding Number and Even-Odd Ray Casting
 * - Segment-polygon edge intersection calculations
 * - Line clipping and classification into inside (blue) and outside (red) paths.
 */

export function isPointInPolygon(
  point: [number, number],
  polygon: [number, number][]
): boolean {
  if (!polygon || polygon.length < 3) return false

  // Ensure polygon ring is closed for iteration
  const poly = [...polygon]
  const first = poly[0]
  const last = poly[poly.length - 1]
  if (first[0] !== last[0] || first[1] !== last[1]) {
    poly.push(first)
  }

  const [px, py] = point
  let windingNumber = 0
  let evenOddInside = false

  for (let i = 0; i < poly.length - 1; i++) {
    const [x1, y1] = poly[i]
    const [x2, y2] = poly[i + 1]

    // Even-Odd Ray Casting
    const intersect =
      y1 > py !== y2 > py &&
      px < ((x2 - x1) * (py - y1)) / (y2 - y1 + 1e-15) + x1
    if (intersect) evenOddInside = !evenOddInside

    // Non-Zero Winding Number
    if (y1 <= py) {
      if (y2 > py) {
        const isLeft = (x2 - x1) * (py - y1) - (px - x1) * (y2 - y1)
        if (isLeft > 1e-12) {
          windingNumber++
        } else if (Math.abs(isLeft) <= 1e-12) {
          return true
        }
      }
    } else {
      if (y2 <= py) {
        const isLeft = (x2 - x1) * (py - y1) - (px - x1) * (y2 - y1)
        if (isLeft < -1e-12) {
          windingNumber--
        } else if (Math.abs(isLeft) <= 1e-12) {
          return true
        }
      }
    }
  }

  return windingNumber !== 0 || evenOddInside
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

  const denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
  if (Math.abs(denom) < 1e-12) return null // Parallel or collinear

  const ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
  const ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom

  const eps = 1e-10
  if (ua >= -eps && ua <= 1 + eps && ub >= -eps && ub <= 1 + eps) {
    const t = Math.max(0, Math.min(1, ua))
    const ix = x1 + t * (x2 - x1)
    const iy = y1 + t * (y2 - y1)
    return { point: [ix, iy], t }
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
    if (Math.hypot(endPt[0] - startPt[0], endPt[1] - startPt[1]) < 1e-12) {
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
        if (Math.hypot(startPt[0] - lastPt[0], startPt[1] - lastPt[1]) > 1e-12) {
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
        if (Math.hypot(startPt[0] - lastPt[0], startPt[1] - lastPt[1]) > 1e-12) {
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

    // Deduplicate intersection points that are extremely close to start/end or previous t
    const tValues: number[] = [0]
    const pts: [number, number][] = [p1]

    for (const inter of intersections) {
      const lastT = tValues[tValues.length - 1]
      if (inter.t - lastT > 1e-8 && 1 - inter.t > 1e-8) {
        tValues.push(inter.t)
        pts.push(inter.point)
      }
    }
    tValues.push(1)
    pts.push(p2)

    // Process each sub-interval
    for (let k = 0; k < tValues.length - 1; k++) {
      const tMid = (tValues[k] + tValues[k + 1]) / 2
      const midPt: [number, number] = [
        p1[0] + tMid * (p2[0] - p1[0]),
        p1[1] + tMid * (p2[1] - p1[1]),
      ]

      const startPt = pts[k]
      const endPt = pts[k + 1]
      const inside = isPointInPolygon(midPt, poly)

      addSegmentToPaths(startPt, endPt, inside)
    }
  }

  // Final flush
  if (currentInsidePath.length >= 2) insideLines.push(currentInsidePath)
  if (currentOutsidePath.length >= 2) outsideLines.push(currentOutsidePath)

  return { inside: insideLines, outside: outsideLines }
}
