import os
import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("PatentMindGraph")


class Neo4jClient:
    """
    Neo4j Community Edition client for the PatentMind knowledge graph.
    Stores patent citation networks, inventor collaboration graphs,
    and CPC/IPC technology domain relationships.
    """

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "patentpassword")
        self.driver = None

        try:
            self.driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
            self._create_constraints()
        except Exception as e:
            logger.warning(f"Neo4j connection failed ({e}). Graph features unavailable.")
            self.driver = None

    def _create_constraints(self):
        """Create uniqueness constraints on first connection."""
        if not self.driver:
            return
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Patent) REQUIRE p.patent_number IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Inventor) REQUIRE i.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Assignee) REQUIRE a.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:CPCCode) REQUIRE c.code IS UNIQUE",
        ]
        with self.driver.session() as session:
            for cypher in constraints:
                try:
                    session.run(cypher)
                except Exception:
                    pass
        logger.info("Neo4j uniqueness constraints ensured.")

    # ── Node Creation ──────────────────────────────────────────────

    def upsert_patent(self, patent: Dict[str, Any]) -> None:
        """Create or merge a Patent node with its metadata."""
        if not self.driver:
            return
        cypher = """
        MERGE (p:Patent {patent_number: $patent_number})
        SET p.title       = $title,
            p.abstract    = $abstract,
            p.assignee    = $assignee,
            p.filing_date = $filing_date,
            p.pub_date    = $publication_date,
            p.source      = $source_repository,
            p.status      = $processing_status
        """
        with self.driver.session() as session:
            session.run(cypher, **patent)

    def upsert_inventor(self, name: str) -> None:
        if not self.driver:
            return
        with self.driver.session() as session:
            session.run("MERGE (i:Inventor {name: $name})", name=name)

    def upsert_assignee(self, name: str) -> None:
        if not self.driver:
            return
        with self.driver.session() as session:
            session.run("MERGE (a:Assignee {name: $name})", name=name)

    def upsert_cpc_code(self, code: str) -> None:
        if not self.driver:
            return
        with self.driver.session() as session:
            session.run("MERGE (c:CPCCode {code: $code})", code=code)

    # ── Relationship Creation ──────────────────────────────────────

    def link_patent_inventor(self, patent_number: str, inventor_name: str) -> None:
        if not self.driver:
            return
        cypher = """
        MATCH (p:Patent {patent_number: $pn})
        MERGE (i:Inventor {name: $inv})
        MERGE (i)-[:INVENTED]->(p)
        """
        with self.driver.session() as session:
            session.run(cypher, pn=patent_number, inv=inventor_name)

    def link_patent_assignee(self, patent_number: str, assignee_name: str) -> None:
        if not self.driver:
            return
        cypher = """
        MATCH (p:Patent {patent_number: $pn})
        MERGE (a:Assignee {name: $asg})
        MERGE (a)-[:OWNS]->(p)
        """
        with self.driver.session() as session:
            session.run(cypher, pn=patent_number, asg=assignee_name)

    def link_patent_cpc(self, patent_number: str, cpc_code: str) -> None:
        if not self.driver:
            return
        cypher = """
        MATCH (p:Patent {patent_number: $pn})
        MERGE (c:CPCCode {code: $cpc})
        MERGE (p)-[:CLASSIFIED_AS]->(c)
        """
        with self.driver.session() as session:
            session.run(cypher, pn=patent_number, cpc=cpc_code)

    # ── Bulk Ingestion ─────────────────────────────────────────────

    def ingest_patent_graph(self, patent: Dict[str, Any]) -> None:
        """
        Full graph ingestion for a single patent record:
        creates Patent node, Inventor nodes, Assignee node,
        CPC nodes, and all relationships.
        """
        pn = patent.get("patent_number", "")
        self.upsert_patent(patent)

        # Inventors
        inventors = patent.get("inventors") or []
        for inv in inventors:
            if inv and inv.strip():
                self.link_patent_inventor(pn, inv.strip())

        # Assignee
        assignee = patent.get("assignee")
        if assignee and assignee.strip():
            self.link_patent_assignee(pn, assignee.strip())

        # CPC codes
        cpc_codes = patent.get("cpc_codes") or []
        for cpc in cpc_codes:
            if cpc and str(cpc).strip():
                self.link_patent_cpc(pn, str(cpc).strip())

    # ── Query Methods ──────────────────────────────────────────────

    def get_patent_network(self, patent_number: str) -> Dict[str, Any]:
        """Return a patent's full graph neighbourhood."""
        if not self.driver:
            return {"patent_number": patent_number, "inventors": [], "assignee": None, "cpc_codes": []}
        cypher = """
        MATCH (p:Patent {patent_number: $pn})
        OPTIONAL MATCH (i:Inventor)-[:INVENTED]->(p)
        OPTIONAL MATCH (a:Assignee)-[:OWNS]->(p)
        OPTIONAL MATCH (p)-[:CLASSIFIED_AS]->(c:CPCCode)
        RETURN p.title AS title,
               collect(DISTINCT i.name) AS inventors,
               collect(DISTINCT a.name) AS assignees,
               collect(DISTINCT c.code) AS cpc_codes
        """
        with self.driver.session() as session:
            result = session.run(cypher, pn=patent_number).single()
            if result:
                return {
                    "patent_number": patent_number,
                    "title": result["title"],
                    "inventors": result["inventors"],
                    "assignees": result["assignees"],
                    "cpc_codes": result["cpc_codes"],
                }
        return {"patent_number": patent_number, "inventors": [], "assignees": [], "cpc_codes": []}

    def find_co_inventors(self, inventor_name: str) -> List[Dict[str, Any]]:
        """Find all inventors who co-invented patents with a given inventor."""
        if not self.driver:
            return []
        cypher = """
        MATCH (i1:Inventor {name: $name})-[:INVENTED]->(p:Patent)<-[:INVENTED]-(i2:Inventor)
        WHERE i1 <> i2
        RETURN DISTINCT i2.name AS co_inventor, collect(p.patent_number) AS shared_patents
        """
        with self.driver.session() as session:
            results = session.run(cypher, name=inventor_name)
            return [{"co_inventor": r["co_inventor"], "shared_patents": r["shared_patents"]} for r in results]

    def find_patents_by_cpc(self, cpc_code: str) -> List[str]:
        """Return all patent numbers classified under a CPC code."""
        if not self.driver:
            return []
        cypher = """
        MATCH (p:Patent)-[:CLASSIFIED_AS]->(c:CPCCode {code: $code})
        RETURN p.patent_number AS pn
        """
        with self.driver.session() as session:
            results = session.run(cypher, code=cpc_code)
            return [r["pn"] for r in results]

    def get_graph_stats(self) -> Dict[str, int]:
        """Return counts for each node label in the knowledge graph."""
        if not self.driver:
            return {"patents": 0, "inventors": 0, "assignees": 0, "cpc_codes": 0}
        stats = {}
        with self.driver.session() as session:
            for label in ["Patent", "Inventor", "Assignee", "CPCCode"]:
                result = session.run(f"MATCH (n:{label}) RETURN count(n) AS cnt").single()
                stats[label.lower()] = result["cnt"] if result else 0
        return stats

    # ── Cleanup ────────────────────────────────────────────────────

    def close(self):
        if self.driver:
            self.driver.close()
            logger.info("Neo4j driver closed.")


_neo4j_instance: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    global _neo4j_instance
    if _neo4j_instance is None:
        _neo4j_instance = Neo4jClient()
    return _neo4j_instance
