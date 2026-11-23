import { useEffect, useMemo, useState } from 'react'
import './SqlLineage.css'

type MappingInfo = {
    fibo_target_kind: 'class' | 'property' | 'relationship'
    fibo_label: string
    rationale: string
    is_cde: boolean
    cde_definition: string | null
    review_status: 'draft' | 'reviewed'
} | null

type ForeignKey = {
    table: string
    field: string
    sourceRef: string
    targetDescription: string
} | null

type LineageField = {
    name: string
    dataType: string
    nullable: boolean
    primaryKey: boolean
    foreignKey: ForeignKey
    sqlComment: string | null
    semanticExample: string | null
    sourceLine: number
    mapping: MappingInfo
    relationshipMapping?: MappingInfo
}

type IncomingRelationship = {
    sourceTable: string
    sourceField: string
    targetField: string
    mapping: MappingInfo
}

type LineageTable = {
    name: string
    description: string
    sourceLine: number
    sourceRef: string
    fields: LineageField[]
    relationships: { field: string; table: string; targetField: string }[]
    incomingRelationships: IncomingRelationship[]
    mapping: MappingInfo
}

type LineageResponse = {
    sourceFile: string
    syntheticOnly: boolean
    lineageScope: string
    summary: { tables: number; fields: number; foreignKeys: number; mappedElements: number; cdes: number }
    tables: LineageTable[]
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export default function SqlLineage() {
    const [lineage, setLineage] = useState<LineageResponse | null>(null)
    const [selectedTableName, setSelectedTableName] = useState('')
    const [selectedFieldName, setSelectedFieldName] = useState('')
    const [error, setError] = useState('')

    useEffect(() => {
        fetch(`${API_BASE}/sql-lineage`)
            .then(async (response) => {
                if (!response.ok) throw new Error(await response.text())
                return await response.json() as LineageResponse
            })
            .then((response) => {
                setLineage(response)
                setSelectedTableName(response.tables[0]?.name ?? '')
                setSelectedFieldName(response.tables[0]?.fields[0]?.name ?? '')
            })
            .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : String(cause)))
    }, [])

    const selectedTable = useMemo(
        () => lineage?.tables.find((table) => table.name === selectedTableName),
        [lineage, selectedTableName],
    )
    const selectedField = selectedTable?.fields.find((field) => field.name === selectedFieldName)

    function selectField(tableName: string, fieldName: string) {
        setSelectedTableName(tableName)
        setSelectedFieldName(fieldName)
    }

    return (
        <div className="sql-lineage-page">
            <header className="sql-lineage-heading">
                <div>
                    <h1>SQL Lineage</h1>
                    <p>Read legacy table and column dependencies alongside saved graph mappings and CDEs.</p>
                </div>
                <span>{lineage?.sourceFile ?? 'Loading legacy SQL…'}</span>
            </header>

            {lineage && (
                <>
                    <div className="sql-lineage-scope">
                        {lineage.syntheticOnly && <strong>Synthetic demo data.</strong>} {lineage.lineageScope} SQL is parsed as source text and is never executed.
                    </div>
                    <div className="sql-lineage-stats">
                        <div><strong>{lineage.summary.tables}</strong><span>Tables</span></div>
                        <div><strong>{lineage.summary.fields}</strong><span>Columns</span></div>
                        <div><strong>{lineage.summary.foreignKeys}</strong><span>Foreign keys</span></div>
                        <div><strong>{lineage.summary.mappedElements}</strong><span>Saved mappings</span></div>
                        <div><strong>{lineage.summary.cdes}</strong><span>CDEs</span></div>
                    </div>
                </>
            )}

            {error && <pre className="sql-lineage-error">{error}</pre>}

            {lineage && selectedTable && (
                <div className="sql-lineage-workspace">
                    <aside className="sql-lineage-table-list">
                        <h2>Legacy tables</h2>
                        {lineage.tables.map((table) => (
                            <button
                                key={table.name}
                                className={selectedTableName === table.name ? 'lineage-table-option selected' : 'lineage-table-option'}
                                onClick={() => selectField(table.name, table.fields[0]?.name ?? '')}
                            >
                                <strong>{table.name}</strong>
                                <span>{table.fields.length} columns{table.mapping ? ' · mapped' : ''}</span>
                            </button>
                        ))}
                    </aside>

                    <section className="sql-lineage-columns">
                        <div className="lineage-section-heading">
                            <div>
                                <span>Table · SQL line {selectedTable.sourceLine}</span>
                                <h2>{selectedTable.name}</h2>
                                <p>{selectedTable.description}</p>
                            </div>
                            {selectedTable.mapping && <span className="lineage-mapping-chip">{selectedTable.mapping.fibo_label}</span>}
                        </div>

                        <div className="lineage-column-list">
                            {selectedTable.fields.map((field) => (
                                <button
                                    key={field.name}
                                    className={selectedFieldName === field.name ? 'lineage-column selected' : 'lineage-column'}
                                    onClick={() => setSelectedFieldName(field.name)}
                                >
                                    <span className="lineage-column-name"><strong>{field.name}</strong><small>{field.dataType}</small></span>
                                    <span className="lineage-column-tags">
                                        {field.primaryKey && <i>PK</i>}
                                        {field.foreignKey && <i>FK</i>}
                                        {field.mapping && <b>{field.mapping.fibo_label}</b>}
                                        {field.mapping?.is_cde && <em>CDE</em>}
                                    </span>
                                </button>
                            ))}
                        </div>

                        <div className="lineage-dependencies">
                            <h3>Table dependencies</h3>
                            {selectedTable.relationships.length === 0 && selectedTable.incomingRelationships.length === 0
                                ? <p>No declared foreign-key dependencies.</p>
                                : <ul>
                                    {selectedTable.relationships.map((relationship) => (
                                        <li key={`${relationship.field}:${relationship.table}`}>
                                            <span>Outgoing</span>
                                            <button onClick={() => selectField(relationship.table, relationship.targetField)}>
                                                {selectedTable.name}.{relationship.field} → {relationship.table}.{relationship.targetField}
                                            </button>
                                            {selectedTable.fields.find((field) => field.name === relationship.field)?.relationshipMapping && (
                                                <b>{selectedTable.fields.find((field) => field.name === relationship.field)?.relationshipMapping?.fibo_label}</b>
                                            )}
                                        </li>
                                    ))}
                                    {selectedTable.incomingRelationships.map((relationship) => (
                                        <li key={`${relationship.sourceTable}:${relationship.sourceField}`}>
                                            <span>Incoming</span>
                                            <button onClick={() => selectField(relationship.sourceTable, relationship.sourceField)}>
                                                {relationship.sourceTable}.{relationship.sourceField} → {selectedTable.name}.{relationship.targetField}
                                            </button>
                                            {relationship.mapping && <b>{relationship.mapping.fibo_label}</b>}
                                        </li>
                                    ))}
                                </ul>}
                        </div>
                    </section>

                    <aside className="sql-lineage-detail">
                        {!selectedField ? <p>Select a column to inspect its lineage.</p> : (
                            <>
                                <span>Column · SQL line {selectedField.sourceLine}</span>
                                <h2>{selectedTable.name}.{selectedField.name}</h2>
                                <p className="lineage-type">{selectedField.dataType}{selectedField.nullable ? ' · nullable' : ' · required'}{selectedField.primaryKey ? ' · primary key' : ''}</p>

                                {selectedField.semanticExample && <div className="lineage-detail-block"><strong>Data dictionary meaning</strong><p>{selectedField.semanticExample}</p></div>}
                                {selectedField.sqlComment && <div className="lineage-detail-block"><strong>SQL comment</strong><p>{selectedField.sqlComment}</p></div>}
                                <div className="lineage-detail-block">
                                    <strong>Declared source</strong>
                                    <p>{lineage.sourceFile} · line {selectedField.sourceLine}</p>
                                </div>

                                {selectedField.foreignKey && (
                                    <div className="lineage-detail-block">
                                        <strong>Foreign-key dependency</strong>
                                        <button className="lineage-jump" onClick={() => selectField(selectedField.foreignKey!.table, selectedField.foreignKey!.field)}>
                                            {selectedTable.name}.{selectedField.name} → {selectedField.foreignKey.table}.{selectedField.foreignKey.field}
                                        </button>
                                        {selectedField.relationshipMapping && <p>Graph relationship: <b>{selectedField.relationshipMapping.fibo_label}</b> · {selectedField.relationshipMapping.review_status}</p>}
                                    </div>
                                )}

                                <div className="lineage-detail-block">
                                    <strong>Ontology mapping</strong>
                                    {selectedField.mapping
                                        ? <>
                                            <p>{selectedField.mapping.fibo_target_kind}: <b>{selectedField.mapping.fibo_label}</b></p>
                                            <p className="lineage-status">{selectedField.mapping.review_status}</p>
                                            {selectedField.mapping.rationale && <p>{selectedField.mapping.rationale}</p>}
                                        </>
                                        : <p>No saved mapping for this column.</p>}
                                </div>

                                {selectedField.mapping?.is_cde && (
                                    <div className="lineage-cde">
                                        <strong>Critical Data Element</strong>
                                        <p>{selectedField.mapping.cde_definition}</p>
                                    </div>
                                )}

                                {selectedTable.incomingRelationships.filter((item) => item.targetField === selectedField.name).length > 0 && (
                                    <div className="lineage-detail-block">
                                        <strong>Referenced by</strong>
                                        {selectedTable.incomingRelationships.filter((item) => item.targetField === selectedField.name).map((item) => (
                                            <button className="lineage-jump" key={`${item.sourceTable}:${item.sourceField}`} onClick={() => selectField(item.sourceTable, item.sourceField)}>
                                                {item.sourceTable}.{item.sourceField}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </>
                        )}
                    </aside>
                </div>
            )}
        </div>
    )
}
