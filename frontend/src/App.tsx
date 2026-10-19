import { useEffect, useState } from 'react'
import TileMap, { type MapData } from './TileMap'

interface MapInfo {
  width: number
  height: number
  tileSize: number
  // Tile name -> tile ID, as used in the tile grid.
  tiles: Record<string, number>
}

// tiles.json maps tile name -> image path relative to scripts/, e.g. "output/...".
type TileImagePaths = Record<string, string>

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url}: ${res.status}`)
  return res.json()
}

function App() {
  const [map, setMap] = useState<MapData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadMap = async () => {
      try {
        const [info, paths] = await Promise.all([
          fetchJson<MapInfo>('/api/map'),
          fetchJson<TileImagePaths>('/api/tiles.json'),
        ])
        const tileImages: string[] = []
        for (const [name, id] of Object.entries(info.tiles)) {
          if (paths[name]) tileImages[id] = `/api/${paths[name]}`
        }
        setMap({
          width: info.width,
          height: info.height,
          tileSize: info.tileSize,
          tileImages,
        })
      } catch {
        setError('Could not reach backend')
      }
    }
    loadMap()
  }, [])

  if (error) return <p>{error}</p>
  if (!map) return <p>Loading...</p>
  return <TileMap map={map} />
}

export default App
