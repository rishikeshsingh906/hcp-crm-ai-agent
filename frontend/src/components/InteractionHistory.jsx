import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { fetchInteractions } from '../store/interactionsSlice'

export default function InteractionHistory() {
  const dispatch = useDispatch()
  const selectedHcpId = useSelector((s) => s.hcp.selectedId)
  const { list } = useSelector((s) => s.interactions)

  useEffect(() => {
    if (selectedHcpId) dispatch(fetchInteractions(selectedHcpId))
  }, [selectedHcpId, dispatch])

  const filtered = list.filter((i) => i.hcp_id === selectedHcpId)

  return (
    <div className="history-list">
      <div className="eyebrow">Recent interactions</div>
      {filtered.length === 0 && (
        <div className="empty-state">No interactions logged yet for this HCP.</div>
      )}
      {filtered.map((i) => (
        <div className="history-item" key={i.id}>
          <div className="meta">
            <span>{i.interaction_date ? new Date(i.interaction_date).toLocaleString() : ''} · {i.channel.replace('_', ' ')} · {i.source}</span>
            <span style={{ display: 'flex', gap: 6 }}>
              {i.compliance_flag && <span className="badge flag">Compliance flag</span>}
              <span className={`badge ${i.sentiment}`}>{i.sentiment}</span>
            </span>
          </div>
          <div>{i.summary}</div>
          {i.topics_discussed?.length > 0 && (
            <div className="topics">
              {i.topics_discussed.map((t, idx) => <span className="topic-pill" key={idx}>{t}</span>)}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
