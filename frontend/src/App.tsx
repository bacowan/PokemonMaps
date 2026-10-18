import { useEffect, useState } from 'react'
import TileMap, { type MapData } from './TileMap'

function App() {
  const [map, setMap] = useState<MapData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadMap = async () => {
      try {
        const res = await fetch('/api/map?width=100&height=100')
        setMap(await res.json())
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
