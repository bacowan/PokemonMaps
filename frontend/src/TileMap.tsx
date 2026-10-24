import { useEffect, useRef, useState } from 'react'
import {
  TransformComponent,
  TransformWrapper,
  useControls,
} from 'react-zoom-pan-pinch'

export interface MapData {
  width: number
  height: number
  tileSize: number
  // Image URL for each tile ID the backend returns.
  tileImages: string[]
}

interface TileRegion {
  x: number
  y: number
  width: number
  height: number
  tiles: number[]
}

interface MetaRegion {
  x: number
  y: number
  width: number
  height: number
  // Field name -> one value per cell, row-major over the region.
  fields: Record<string, unknown[]>
}

// The cell under the pointer, and where on screen the pointer is.
interface Hover {
  x: number
  y: number
  clientX: number
  clientY: number
}

interface View {
  scale: number
  positionX: number
  positionY: number
}

// Per-tile fetch status.
const NOT_LOADED = 0
const REQUESTED = 1
const LOADED = 2

const FETCH_DEBOUNCE_MS = 100
// Screen pixels per map pixel on load; 3 shows ~40 tiles across a 1920px screen.
const INITIAL_SCALE = 3
// Debug mode (?debug=true) fetches per-cell metadata and draws grid lines.
const DEBUG = new URLSearchParams(window.location.search).get('debug') === 'true'
// Grid lines are hidden when tiles are smaller than this many screen pixels.
const MIN_GRID_TILE_PX = 6
const GRID_COLOR = 'rgba(0, 0, 0, 0.35)'

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

function MapControls() {
  const { zoomIn, zoomOut, fitToView } = useControls()
  return (
    <div className="map-controls">
      <button onClick={() => zoomIn()} title="Zoom in">+</button>
      <button onClick={() => zoomOut()} title="Zoom out">−</button>
      <button onClick={() => fitToView()} title="Fit map to screen">⤢</button>
    </div>
  )
}

// The pan/zoom library transforms an empty map-sized div; a screen-sized canvas
// on top draws just the tiles in view, so memory doesn't grow with the map.
function TileMap({ map }: { map: MapData }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [error, setError] = useState<string | null>(null)
  const grid = useRef(new Uint8Array(0))
  const status = useRef(new Uint8Array(0))
  // Field name -> value per map cell (row-major); filled alongside the grid.
  const meta = useRef<Record<string, unknown[]>>({})
  const images = useRef<(HTMLImageElement | undefined)[]>([])
  const view = useRef<View | null>(null)
  const frame = useRef(0)
  const fetchTimer = useRef<number | undefined>(undefined)
  const pointer = useRef<{ clientX: number; clientY: number } | null>(null)
  const [hover, setHover] = useState<Hover | null>(null)

  const visibleRect = (v: View, screenWidth: number, screenHeight: number) => {
    const px = map.tileSize * v.scale
    return {
      x0: Math.max(0, Math.floor(-v.positionX / px)),
      y0: Math.max(0, Math.floor(-v.positionY / px)),
      x1: Math.min(map.width, Math.ceil((screenWidth - v.positionX) / px)),
      y1: Math.min(map.height, Math.ceil((screenHeight - v.positionY) / px)),
    }
  }

  const draw = () => {
    const canvas = canvasRef.current
    const v = view.current
    if (!canvas || !v) return
    const dpr = window.devicePixelRatio || 1
    const { clientWidth, clientHeight } = canvas
    const width = Math.round(clientWidth * dpr)
    const height = Math.round(clientHeight * dpr)
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width
      canvas.height = height
    }
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.imageSmoothingEnabled = false
    ctx.clearRect(0, 0, width, height)

    // Edges are rounded in device pixels so neighbouring tiles never leave seams.
    const { x0, y0, x1, y1 } = visibleRect(v, clientWidth, clientHeight)
    const px = map.tileSize * v.scale
    const edgeX = (x: number) => Math.round((v.positionX + x * px) * dpr)
    const edgeY = (y: number) => Math.round((v.positionY + y * px) * dpr)
    for (let y = y0; y < y1; y++) {
      const top = edgeY(y)
      const tileHeight = edgeY(y + 1) - top
      for (let x = x0; x < x1; x++) {
        const i = y * map.width + x
        if (status.current[i] !== LOADED) continue
        const img = images.current[grid.current[i]]
        if (!img) continue
        const left = edgeX(x)
        ctx.drawImage(img, left, top, edgeX(x + 1) - left, tileHeight)
      }
    }

    if (DEBUG && px >= MIN_GRID_TILE_PX && x1 > x0 && y1 > y0) {
      // Offset by half a pixel so 1px lines land on whole device pixels.
      ctx.beginPath()
      for (let x = x0; x <= x1; x++) {
        ctx.moveTo(edgeX(x) + 0.5, edgeY(y0))
        ctx.lineTo(edgeX(x) + 0.5, edgeY(y1))
      }
      for (let y = y0; y <= y1; y++) {
        ctx.moveTo(edgeX(x0), edgeY(y) + 0.5)
        ctx.lineTo(edgeX(x1), edgeY(y) + 0.5)
      }
      ctx.lineWidth = 1
      ctx.strokeStyle = GRID_COLOR
      ctx.stroke()
    }
  }

  // Points the tooltip at the cell under the last pointer position, which
  // changes when either the pointer or the view moves.
  const updateHover = () => {
    const p = pointer.current
    const v = view.current
    if (!DEBUG || !p || !v) return
    const px = map.tileSize * v.scale
    const x = Math.floor((p.clientX - v.positionX) / px)
    const y = Math.floor((p.clientY - v.positionY) / px)
    if (x < 0 || y < 0 || x >= map.width || y >= map.height) {
      setHover(null)
      return
    }
    setHover({ x, y, clientX: p.clientX, clientY: p.clientY })
  }

  const scheduleDraw = () => {
    if (frame.current) return
    frame.current = requestAnimationFrame(() => {
      frame.current = 0
      draw()
    })
  }

  const fetchVisible = async () => {
    const canvas = canvasRef.current
    const v = view.current
    if (!canvas || !v) return
    const { x0, y0, x1, y1 } = visibleRect(v, canvas.clientWidth, canvas.clientHeight)
    if (x1 <= x0 || y1 <= y0) return

    // Write into the arrays current at request time, in case the map changes.
    const regionGrid = grid.current
    const regionStatus = status.current
    const regionMeta = meta.current
    let needed = false
    for (let y = y0; y < y1; y++) {
      for (let x = x0; x < x1; x++) {
        const i = y * map.width + x
        if (regionStatus[i] === NOT_LOADED) {
          regionStatus[i] = REQUESTED
          needed = true
        }
      }
    }
    if (!needed) return

    const params = new URLSearchParams({
      x: String(x0),
      y: String(y0),
      width: String(x1 - x0),
      height: String(y1 - y0),
    })
    const fetchRegion = async <T,>(url: string): Promise<T> => {
      const res = await fetch(url)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return res.json()
    }
    let region: TileRegion
    let metaRegion: MetaRegion | null
    try {
      ;[region, metaRegion] = await Promise.all([
        fetchRegion<TileRegion>(`/api/map/tiles?${params}`),
        DEBUG ? fetchRegion<MetaRegion>(`/api/map/meta?${params}`) : null,
      ])
    } catch {
      for (let y = y0; y < y1; y++) {
        for (let x = x0; x < x1; x++) {
          const i = y * map.width + x
          if (regionStatus[i] === REQUESTED) regionStatus[i] = NOT_LOADED
        }
      }
      setError('Could not load tiles')
      return
    }
    region.tiles.forEach((tile, n) => {
      const x = region.x + (n % region.width)
      const y = region.y + Math.floor(n / region.width)
      const i = y * map.width + x
      regionGrid[i] = tile
      regionStatus[i] = LOADED
    })
    if (metaRegion) {
      const { x, y, width, fields } = metaRegion
      for (const [field, values] of Object.entries(fields)) {
        const cells = (regionMeta[field] ??= new Array(map.width * map.height))
        values.forEach((value, n) => {
          cells[(y + Math.floor(n / width)) * map.width + x + (n % width)] = value
        })
      }
      updateHover()
    }
    scheduleDraw()
  }

  const scheduleFetch = () => {
    clearTimeout(fetchTimer.current)
    fetchTimer.current = window.setTimeout(fetchVisible, FETCH_DEBOUNCE_MS)
  }

  const onViewChange = (v: View) => {
    view.current = v
    scheduleDraw()
    scheduleFetch()
    updateHover()
  }

  useEffect(() => {
    let cancelled = false
    grid.current = new Uint8Array(map.width * map.height)
    status.current = new Uint8Array(map.width * map.height)
    meta.current = {}
    images.current = []
    map.tileImages.forEach((src, id) => {
      loadImage(src).then(
        (img) => {
          if (cancelled) return
          images.current[id] = img
          scheduleDraw()
        },
        () => {
          if (!cancelled) setError('Could not load tile images')
        },
      )
    })
    // The initial layout may have fired before this effect (or been cancelled by
    // a StrictMode remount), so fetch for whatever view we last saw.
    if (view.current) {
      scheduleDraw()
      scheduleFetch()
    }
    // The canvas fills the window, so client coordinates are canvas coordinates.
    const onPointerMove = (e: PointerEvent) => {
      pointer.current = { clientX: e.clientX, clientY: e.clientY }
      updateHover()
    }
    // A pointerout with nowhere to go means the pointer left the window.
    const onPointerOut = (e: PointerEvent) => {
      if (e.relatedTarget) return
      pointer.current = null
      setHover(null)
    }
    window.addEventListener('resize', scheduleDraw)
    window.addEventListener('resize', scheduleFetch)
    if (DEBUG) {
      window.addEventListener('pointermove', onPointerMove)
      window.addEventListener('pointerout', onPointerOut)
    }
    return () => {
      cancelled = true
      clearTimeout(fetchTimer.current)
      cancelAnimationFrame(frame.current)
      frame.current = 0
      window.removeEventListener('resize', scheduleDraw)
      window.removeEventListener('resize', scheduleFetch)
      window.removeEventListener('pointermove', onPointerMove)
      window.removeEventListener('pointerout', onPointerOut)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map])

  if (error) return <p>{error}</p>
  return (
    <TransformWrapper
      initialScale={INITIAL_SCALE}
      centerOnInit
      minScale={0.1}
      maxScale={16}
      limitToBounds={false}
      keyboard={{ disabled: false }}
      doubleClick={{ mode: 'zoomIn' }}
      onInit={(ref) => onViewChange(ref.state)}
      onTransform={(_ref, state) => onViewChange(state)}
    >
      <TransformComponent wrapperStyle={{ width: '100vw', height: '100vh' }}>
        <div
          style={{
            width: map.width * map.tileSize,
            height: map.height * map.tileSize,
          }}
        />
      </TransformComponent>
      <canvas ref={canvasRef} className="map-canvas" />
      {hover && (
        <div
          className="map-tooltip"
          style={{ left: hover.clientX + 14, top: hover.clientY + 14 }}
        >
          <div className="map-tooltip-cell">
            {hover.x}, {hover.y}
          </div>
          {Object.entries(meta.current).map(([field, cells]) => (
            <div key={field}>
              {field}: {String(cells[hover.y * map.width + hover.x] ?? '…')}
            </div>
          ))}
        </div>
      )}
      <MapControls />
    </TransformWrapper>
  )
}

export default TileMap
