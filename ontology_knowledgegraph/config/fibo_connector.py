from neo4j import GraphDatabase
from config.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

class FiboConnector:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI,auth=(NEO4J_USER, NEO4J_PASSWORD))

    def run(self, cypher: str, parameters: dict|None=None)->list[dict]:
        with self.driver.session() as session:
            result = session.run(cypher, parameters or {}) # type: ignore
            return [record.data() for record in result]

    def close(self) -> None: self.driver.close()