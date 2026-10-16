import { useEffect, useRef } from 'react'

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

function TileMap({ map }: { map: MapData }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    let cancelled = false
    const unique = [...new Set(map.tiles)]

    Promise.all(unique.map((t) => loadImage(`/api/tilesets/${t}`))).then(
      (images) => {
        const ctx = canvasRef.current?.getContext('2d')
        if (cancelled || !ctx) return
        const byPath = new Map(unique.map((t, i) => [t, images[i]]))
        map.tiles.forEach((tile, i) => {
          const x = (i % map.width) * map.tileSize
          const y = Math.floor(i / map.width) * map.tileSize
          ctx.drawImage(byPath.get(tile)!, x, y)
        })
      },
    )
    return () => {
      cancelled = true
    }
  }, [map])

  return (
    <canvas
      ref={canvasRef}
      width={map.width * map.tileSize}
      height={map.height * map.tileSize}
      style={{ imageRendering: 'pixelated' }}
    />
  )
}

export default TileMap
