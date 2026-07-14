import LogInteractionScreen from './components/LogInteractionScreen'

export default function App() {
  return (
    <div className="app-shell">
      <div className="topbar">
        <div className="mark">Rx</div>
        <span className="title">HCP CRM</span>
        <span className="subtitle">AI-first field rep console</span>
      </div>
      <LogInteractionScreen />
    </div>
  )
}
