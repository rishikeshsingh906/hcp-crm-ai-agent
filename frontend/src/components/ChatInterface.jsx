import { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { addUserMessage, sendChatMessage } from '../store/chatSlice'
import { fetchInteractions } from '../store/interactionsSlice'

export default function ChatInterface() {
  const dispatch = useDispatch()
  const { messages, status } = useSelector((s) => s.chat)
  const selectedHcpId = useSelector((s) => s.hcp.selectedId)
  const [draft, setDraft] = useState('')
  const logRef = useRef(null)

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    const text = draft.trim()
    if (!text || status === 'loading') return
    dispatch(addUserMessage(text))
    const history = [...messages, { role: 'user', content: text }].map(
      ({ role, content }) => ({ role, content })
    )
    setDraft('')
    dispatch(sendChatMessage({ messages: history, hcpId: selectedHcpId, repName: 'Field Rep' }))
      .then(() => dispatch(fetchInteractions(selectedHcpId)))
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="card chat-window">
      <div className="chat-log" ref={logRef}>
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            {m.toolCalls?.length > 0 && (
              <div>
                {m.toolCalls.map((tc, j) => (
                  <span className="tool-tag" key={j}>{tc.name}</span>
                ))}
              </div>
            )}
            {m.content}
          </div>
        ))}
        {status === 'loading' && <div className="bubble assistant">Thinking…</div>}
      </div>
      <div className="chat-input-row">
        <textarea
          placeholder="Describe the visit… (Enter to send, Shift+Enter for a new line)"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="btn-primary" onClick={handleSend} disabled={status === 'loading'}>Send</button>
      </div>
    </div>
  )
}
