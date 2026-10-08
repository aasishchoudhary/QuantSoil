"""PostgreSQL sink for low-cardinality analyst access audit events."""
from datetime import datetime

class AnalystAuditRepositoryError(RuntimeError): pass

class PostgresAnalystAuditRepository:
    def __init__(self, connection): self.connection=connection
    def put(self, *, occurred_at:datetime, method:str, path:str, status_code:int, correlation_id:str):
        if not method or not path or not correlation_id: raise AnalystAuditRepositoryError("audit fields are required")
        q="""INSERT INTO analyst_audit
        (occurred_at,method,path,status_code,correlation_id)
        VALUES (%s,%s,%s,%s,%s)"""
        try:
            with self.connection.cursor() as c:c.execute(q,(occurred_at,method,path,status_code,correlation_id))
            self.connection.commit()
        except Exception as exc:
            try:self.connection.rollback()
            except Exception:pass
            raise AnalystAuditRepositoryError("failed to persist analyst audit event") from exc
