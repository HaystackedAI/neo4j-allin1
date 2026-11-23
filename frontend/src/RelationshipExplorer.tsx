import { useState } from 'react'

type Connection = {
    relationshipType: string
    direction: 'incoming' | 'outgoing'
    relationshipProperties: Record<string, unknown>
    node: {
        label: string
        id: string
        name: string | null
    }
}

type Props = {
    nodeLabel: string
    nodeId: string
    displayName: string
    ancestorKeys?: string[]
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export default function RelationshipExplorer({
    nodeLabel,
    nodeId,
    ancestorKeys = [],
}: Props) {
    const [expanded, setExpanded] = useState(false)
    const [connections, setConnections] = useState<Connection[]>([])
    const [loaded, setLoaded] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const nodeKey = `${nodeLabel}:${nodeId}`

    async function toggleConnections() {
        if (expanded) {
            setExpanded(false)
            return
        }

        if (!loaded) {
            setLoading(true)
            setError('')
            try {
                const response = await fetch(
                    `${API_BASE}/loan/nodes/${encodeURIComponent(nodeLabel)}/${encodeURIComponent(nodeId)}/connections`,
                )
                if (!response.ok) throw new Error(await response.text())
                setConnections(await response.json() as Connection[])
                setLoaded(true)
            } catch (cause) {
                setError(cause instanceof Error ? cause.message : String(cause))
                setLoading(false)
                return
            }
            setLoading(false)
        }

        setExpanded(true)
    }

    return (
        <div className="relationship-explorer">
            <button className="expand-connections" onClick={() => void toggleConnections()}>
                {loading ? 'Loading…' : expanded ? 'Hide connections' : 'Expand connections'}
            </button>
            {error && <div className="connection-error">{error}</div>}
            {expanded && (
                connections.length === 0 ? (
                    <div className="connection-empty">No connected entities.</div>
                ) : (
                    <ul className="connection-list">
                        {connections.map((connection, index) => {
                            const neighborKey = `${connection.node.label}:${connection.node.id}`
                            const isAncestor = ancestorKeys.includes(neighborKey) || neighborKey === nodeKey
                            return (
                                <li key={`${connection.relationshipType}:${neighborKey}:${index}`}>
                                    <div className="connection-edge">
                                        {connection.direction} {connection.relationshipType}
                                        {Object.keys(connection.relationshipProperties).length > 0 && (
                                            <span> {JSON.stringify(connection.relationshipProperties)}</span>
                                        )}
                                    </div>
                                    <div className="connection-node">
                                        <strong>{connection.node.name || connection.node.id}</strong>
                                        <span>{connection.node.label} · {connection.node.id}</span>
                                    </div>
                                    {isAncestor ? (
                                        <div className="connection-cycle">Already shown in this path.</div>
                                    ) : (
                                        <RelationshipExplorer
                                            nodeLabel={connection.node.label}
                                            nodeId={connection.node.id}
                                            displayName={connection.node.name || connection.node.id}
                                            ancestorKeys={[...ancestorKeys, nodeKey]}
                                        />
                                    )}
                                </li>
                            )
                        })}
                    </ul>
                )
            )}
        </div>
    )
}
