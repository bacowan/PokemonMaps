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
  const images = useRef<(HTMLImageElement | undefined)[]>([])
  const view = useRef<View | null>(null)
  const frame = useRef(0)
  const fetchTimer = useRef<number | undefined>(undefined)

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
    let region: TileRegion
    try {
      const res = await fetch(`/api/map/tiles?${params}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      region = await res.json()
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
  }

  useEffect(() => {
    let cancelled = false
    grid.current = new Uint8Array(map.width * map.height)
    status.current = new Uint8Array(map.width * map.height)
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
    window.addEventListener('resize', scheduleDraw)
    window.addEventListener('resize', scheduleFetch)
    return () => {
      cancelled = true
      clearTimeout(fetchTimer.current)
      cancelAnimationFrame(frame.current)
      frame.current = 0
      window.removeEventListener('resize', scheduleDraw)
      window.removeEventListener('resize', scheduleFetch)
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
      <MapControls />
    </TransformWrapper>
  )
}

export default TileMap
