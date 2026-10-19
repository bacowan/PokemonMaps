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
  tiles: string[]
}

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

  useEffect(() => {
    let cancelled = false
    setError(null)
    const unique = [...new Set(map.tiles)]

    const draw = async () => {
      let images: HTMLImageElement[]
      try {
        images = await Promise.all(
          unique.map((t) => loadImage(`/api/tilesets/${t}`)),
        )
      } catch {
        if (!cancelled) setError('Could not load tiles')
        return
      }
      const ctx = canvasRef.current?.getContext('2d')
      if (cancelled || !ctx) return
      const byPath = new Map(unique.map((t, i) => [t, images[i]]))
      map.tiles.forEach((tile, i) => {
        const x = (i % map.width) * map.tileSize
        const y = Math.floor(i / map.width) * map.tileSize
        ctx.drawImage(byPath.get(tile)!, x, y)
      })
    }
    draw()
    return () => {
      cancelled = true
    }
  }, [map])

  if (error) return <p>{error}</p>
  return (
    <TransformWrapper
      fitOnInit
      minScale={0.1}
      maxScale={16}
      limitToBounds={false}
      keyboard={{ disabled: false }}
      doubleClick={{ mode: 'zoomIn' }}
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
