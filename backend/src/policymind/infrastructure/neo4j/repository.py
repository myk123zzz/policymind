from collections.abc import Sequence

from policymind.graph.repository import GraphPath


class Neo4jGraphRepository:
    """Neo4j 图谱存储适配器。"""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self.uri = uri
        self.user = user
        self.password = password

    async def upsert(
        self,
        entities: Sequence[dict[str, object]],
        relations: Sequence[dict[str, object]],
    ) -> None:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        with driver.session() as session:

            def _upsert(tx):  # type: ignore[no-untyped-def]
                for e in entities:
                    etype = str(e["type"])
                    eq = f"MERGE (n:{etype} {{id: $id}}) SET n += $props"
                    tx.run(
                        eq,
                        id=str(e["id"]),
                        props={k: v for k, v in e.items() if k not in ("id", "type")},
                    )
                for r in relations:
                    rtype = str(r["type"])
                    rq = (
                        "MATCH (a {id: $src}), (b {id: $tgt}) "
                        f"MERGE (a)-[rel:{rtype}]->(b) SET rel += $props"
                    )
                    tx.run(
                        rq,
                        src=str(r["source"]),
                        tgt=str(r["target"]),
                        props={
                            k: v
                            for k, v in r.items()
                            if k not in ("source", "target", "type")
                        },
                    )

            session.execute_write(_upsert)
        driver.close()

    async def search_paths(
        self,
        *,
        tenant_id: int,
        seed_entity_ids: Sequence[str],
        max_hops: int,
        limit: int,
    ) -> list[GraphPath]:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        with driver.session() as session:

            def _search(tx):  # type: ignore[no-untyped-def]
                results = []
                for sid in seed_entity_ids:
                    query = (
                        f"MATCH p=(start {{id: $sid, tenant_id: $tid}})-[*1..{max_hops}]-(end) "
                        "RETURN nodes(p) as entities, relationships(p) as relations LIMIT $limit"
                    )
                    recs = tx.run(query, sid=str(sid), tid=tenant_id, limit=limit)
                    for rec in recs:
                        results.append(
                            GraphPath(
                                entities=[dict(n) for n in rec["entities"]],
                                relations=[dict(r) for r in rec["relations"]],
                            )
                        )
                return results

            paths = session.execute_read(_search)
        driver.close()
        return paths  # type: ignore[no-any-return]
