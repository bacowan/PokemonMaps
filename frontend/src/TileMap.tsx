import { useEffect, useRef, useState } from 'react'
import {
  TransformComponent,
  TransformWrapper,
  useControls,
  type ReactZoomPanPinchRef,
} from 'react-zoom-pan-pinch'

export interface MapData {
  width: number
  height: number
  tileSize: number
}

interface TileRegion {
  x: number
  y: number
  width: number
  height: number
  tiles: string[]
}

const TILE_PATH = '/api/tilesets/primary/general/metatiles'
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

function TileMap({ map }: { map: MapData }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [error, setError] = useState<string | null>(null)
  const images = useRef(new Map<string, Promise<HTMLImageElement>>())
  const drawn = useRef(new Uint8Array(map.width * map.height))
  const fetchTimer = useRef<number | undefined>(undefined)
  const latestView = useRef<ReactZoomPanPinchRef | null>(null)

  useEffect(() => {
    drawn.current = new Uint8Array(map.width * map.height)
    // The initial fit may have fired before this effect (or been cancelled by a
    // StrictMode remount), so fetch for whatever view we last saw.
    if (latestView.current) scheduleFetch(latestView.current)
    return () => clearTimeout(fetchTimer.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map])

  const getImage = (name: string): Promise<HTMLImageElement> => {
    let img = images.current.get(name)
    if (!img) {
      img = loadImage(`${TILE_PATH}/${name}.png`)
      images.current.set(name, img)
    }
    return img
  }

  const loadRegion = async (
    x: number,
    y: number,
    width: number,
    height: number,
  ) => {
    let region: TileRegion
    let byName: Map<string, HTMLImageElement>
    try {
      const params = new URLSearchParams({
        x: String(x),
        y: String(y),
        width: String(width),
        height: String(height),
      })
      const res = await fetch(`/api/map/tiles?${params}`)
      region = await res.json()
      const unique = [...new Set(region.tiles)]
      const loaded = await Promise.all(unique.map(getImage))
      byName = new Map(unique.map((t, i) => [t, loaded[i]]))
    } catch {
      setError('Could not load tiles')
      return
    }
    const ctx = canvasRef.current?.getContext('2d')
    if (!ctx) return
    region.tiles.forEach((tile, i) => {
      const tx = region.x + (i % region.width)
      const ty = region.y + Math.floor(i / region.width)
      ctx.drawImage(byName.get(tile)!, tx * map.tileSize, ty * map.tileSize)
      drawn.current[ty * map.width + tx] = 1
    })
  }

  const fetchVisible = (ref: ReactZoomPanPinchRef) => {
    const wrapper = ref.instance.wrapperComponent
    if (!wrapper) return
    const { scale, positionX, positionY } = ref.state
    const px = map.tileSize * scale
    const x0 = Math.max(0, Math.floor(-positionX / px))
    const y0 = Math.max(0, Math.floor(-positionY / px))
    const x1 = Math.min(map.width, Math.ceil((wrapper.clientWidth - positionX) / px))
    const y1 = Math.min(map.height, Math.ceil((wrapper.clientHeight - positionY) / px))
    if (x1 <= x0 || y1 <= y0) return

    let needed = false
    for (let y = y0; y < y1 && !needed; y++) {
      for (let x = x0; x < x1; x++) {
        if (!drawn.current[y * map.width + x]) {
          needed = true
          break
        }
      }
    }
    if (needed) loadRegion(x0, y0, x1 - x0, y1 - y0)
  }

  const scheduleFetch = (ref: ReactZoomPanPinchRef) => {
    latestView.current = ref
    clearTimeout(fetchTimer.current)
    fetchTimer.current = window.setTimeout(
      () => fetchVisible(ref),
      FETCH_DEBOUNCE_MS,
    )
  }

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
      onInit={scheduleFetch}
      onTransform={scheduleFetch}
    >
      <TransformComponent wrapperStyle={{ width: '100vw', height: '100vh' }}>
        <canvas
          ref={canvasRef}
          width={map.width * map.tileSize}
          height={map.height * map.tileSize}
          style={{ imageRendering: 'pixelated' }}
        />
      </TransformComponent>
      <MapControls />
    </TransformWrapper>
  )
}

export default TileMap
