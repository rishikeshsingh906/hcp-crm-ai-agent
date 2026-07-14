import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { fetchHcps, selectHcp } from '../store/hcpSlice'

export default function HcpSelector() {
  const dispatch = useDispatch()
  const { list, selectedId, status } = useSelector((s) => s.hcp)

  useEffect(() => {
    if (status === 'idle') dispatch(fetchHcps())
  }, [status, dispatch])

  const selected = list.find((h) => h.id === selectedId)

  return (
    <div className="hcp-picker">
      <select
        value={selectedId || ''}
        onChange={(e) => dispatch(selectHcp(Number(e.target.value)))}
      >
        {list.length === 0 && <option value="">Loading HCPs…</option>}
        {list.map((h) => (
          <option key={h.id} value={h.id}>{h.name} — {h.specialty}</option>
        ))}
      </select>
      {selected && (
        <span className="hcp-chip">{selected.institution} · prefers {selected.preferred_channel}</span>
      )}
    </div>
  )
}
