import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { createInteraction } from '../store/interactionsSlice'

const CHANNELS = ['in_person', 'virtual', 'phone', 'email', 'conference']

export default function StructuredForm() {
  const dispatch = useDispatch()
  const selectedHcpId = useSelector((s) => s.hcp.selectedId)
  const submitStatus = useSelector((s) => s.interactions.submitStatus)
  const lastSaved = useSelector((s) => s.interactions.lastSaved)

  const [channel, setChannel] = useState('in_person')
  const [repName, setRepName] = useState('Field Rep')
  const [notes, setNotes] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!selectedHcpId || !notes.trim()) return
    dispatch(createInteraction({
      hcp_id: selectedHcpId,
      channel,
      rep_name: repName,
      raw_notes: notes,
      source: 'form',
    })).then(() => setNotes(''))
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <div className="field-row">
        <div className="field">
          <label>Channel</label>
          <select value={channel} onChange={(e) => setChannel(e.target.value)}>
            {CHANNELS.map((c) => <option key={c} value={c}>{c.replace('_', ' ')}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Rep name</label>
          <input value={repName} onChange={(e) => setRepName(e.target.value)} />
        </div>
      </div>

      <div className="field">
        <label>Visit notes</label>
        <textarea
          placeholder="e.g. Discussed the new cardiac trial results, HCP was receptive, distributed 2 sample packs of Cardolex, follow up with the Phase III data in two weeks."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>

      <button type="submit" className="btn-primary" disabled={submitStatus === 'loading' || !notes.trim()}>
        {submitStatus === 'loading' ? 'Summarizing & saving…' : 'Save interaction'}
      </button>

      {lastSaved && submitStatus === 'succeeded' && (
        <div style={{ marginTop: 16, fontSize: 13, color: 'var(--color-ink-soft)' }}>
          Saved. AI summary: <em>{lastSaved.summary}</em>
        </div>
      )}
    </form>
  )
}
