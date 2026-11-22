import { useEffect, useState, type KeyboardEvent } from 'react'
import './App.css'

type SavedQuery = {
    id: number
    name: string
    cypher: string
    created_at: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

function App() {
    const [query, setQuery] = useState('')
    const [queryName, setQueryName] = useState('')
    const [result, setResult] = useState<unknown>(null)
    const [savedQueries, setSavedQueries] = useState<SavedQuery[]>([])
    const [error, setError] = useState('')
    const [running, setRunning] = useState(false)

    async function loadSavedQueries() {
        const response = await fetch(`${API_BASE}/neo4j/saved-queries`)
        if (!response.ok) throw new Error(await response.text())
        setSavedQueries(await response.json() as SavedQuery[])
    }

    useEffect(() => {
        loadSavedQueries().catch((cause: unknown) => {
            setError(cause instanceof Error ? cause.message : String(cause))
        })
    }, [])

    async function runQuery(cypher = query) {
        if (!cypher.trim()) return
        setRunning(true)
        setError('')
        try {
            const response = await fetch(`${API_BASE}/neo4j/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cypher, parameters: {} }),
            })
            const body = await response.json()
            if (!response.ok) throw new Error(JSON.stringify(body))
            setResult(body)
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : String(cause))
        } finally {
            setRunning(false)
        }
    }

    async function saveQuery() {
        if (!query.trim() || !queryName.trim()) return
        setError('')
        try {
            const response = await fetch(`${API_BASE}/neo4j/saved-queries`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: queryName.trim(), cypher: query }),
            })
            if (!response.ok) throw new Error(await response.text())
            setQueryName('')
            await loadSavedQueries()
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : String(cause))
        }
    }

    async function deleteQuery(id: number) {
        setError('')
        try {
            const response = await fetch(`${API_BASE}/neo4j/saved-queries/${id}`, { method: 'DELETE' })
            if (!response.ok) throw new Error(await response.text())
            await loadSavedQueries()
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : String(cause))
        }
    }

    function handleQueryKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            void runQuery()
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
                <button className="run-query" onClick={() => void runQuery()} disabled={running}>
                    {running ? 'Running…' : 'Run query'}
                </button>
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
                    {error && <pre className="error-output">{error}</pre>}
                    <div className="panes">
                        <section className="pane result-pane">
                            <h2>Query result</h2>
                            <pre className="result-output">{result === null ? 'Run a Cypher query to see its returned records.' : JSON.stringify(result, null, 2)}</pre>
                        </section>
                        <section className="pane saved-pane">
                            <h2>Saved Cypher queries</h2>
                            <div className="save-query-form">
                                <input aria-label="Saved query name" placeholder="Query name" value={queryName} onChange={(event) => setQueryName(event.target.value)} />
                                <button onClick={() => void saveQuery()} disabled={!query.trim() || !queryName.trim()}>Save current query</button>
                            </div>
                            <div className="table-scroll">
                                <table>
                                    <thead><tr><th>Name</th><th>Cypher</th><th>Actions</th></tr></thead>
                                    <tbody>
                                        {savedQueries.map((saved) => (
                                            <tr key={saved.id}>
                                                <td>{saved.name}</td>
                                                <td><code>{saved.cypher}</code></td>
                                                <td className="row-actions">
                                                    <button onClick={() => { setQuery(saved.cypher); void runQuery(saved.cypher) }}>Run</button>
                                                    <button className="delete-query" onClick={() => void deleteQuery(saved.id)}>Delete</button>
                                                </td>
                                            </tr>
                                        ))}
                                        {savedQueries.length === 0 && <tr><td colSpan={3}>No saved queries.</td></tr>}
                                    </tbody>
                                </table>
                            </div>
                        </section>
                    </div>
                </main>
            </div>
        </div>
    )
}

export default App
