import { useState, type KeyboardEvent } from 'react'
import './App.css'

function App() {
    const [query, setQuery] = useState('')

    function runQuery() {
        if (!query.trim()) return
        console.log('Run Cypher query:', query)
    }

    function handleQueryKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            runQuery()
        }
    }

    return (

        <div className="app">
            <header className="topbar">
                <strong className="brand">Knowledge Graph</strong>
                <textarea
                    className="search"
                    placeholder="Enter Cypher query..."
                    rows={4}
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    onKeyDown={handleQueryKeyDown}
                />
                <button className="run-query" onClick={runQuery}>Run query</button>
            </header>

            <div className="workspace">
                <nav className="sidebar">
                    <a className="nav-link active" href="#explore">Explore</a>
                    <a className="nav-link" href="#curate">Curate</a>
                    <a className="nav-link" href="#govern">Govern</a>
                    <a className="nav-link" href="#chat">Chat</a>
                    <a className="nav-link" href="#admin">Admin</a>
                </nav>

                <main className="content">
                    <h1>Explore</h1>
                </main>
            </div>
        </div>
    )
}

export default App
