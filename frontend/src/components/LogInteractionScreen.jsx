import { useState } from 'react'
import HcpSelector from './HcpSelector'
import StructuredForm from './StructuredForm'
import ChatInterface from './ChatInterface'
import InteractionHistory from './InteractionHistory'

export default function LogInteractionScreen() {
  const [mode, setMode] = useState('form') // 'form' | 'chat'

  return (
    <div className="page">
      <div className="eyebrow">HCP Module</div>
      <h1 className="screen-title">Log Interaction</h1>
      <p className="screen-desc">
        Record a visit using a structured form, or just describe what happened —
        the AI agent will extract the details and log it for you.
      </p>

      <HcpSelector />

      <div className="mode-toggle" role="tablist" aria-label="Logging mode">
        <button
          role="tab"
          aria-selected={mode === 'form'}
          className={mode === 'form' ? 'active' : ''}
          onClick={() => setMode('form')}
        >
          Structured form
        </button>
        <button
          role="tab"
          aria-selected={mode === 'chat'}
          className={mode === 'chat' ? 'active' : ''}
          onClick={() => setMode('chat')}
        >
          Conversational
        </button>
      </div>

      {mode === 'form' ? <StructuredForm /> : <ChatInterface />}

      <InteractionHistory />
    </div>
  )
}
