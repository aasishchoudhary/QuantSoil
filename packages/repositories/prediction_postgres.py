"""PostgreSQL persistence for predictions and their verified scores."""
from __future__ import annotations
import json
import math
from packages.contracts.event import Event
from services.prediction.baseline import BinaryForecast

class PredictionRepositoryError(RuntimeError): pass

class PostgresPredictionRepository:
    def __init__(self, connection): self.connection=connection

    def put(self, forecast: BinaryForecast)->BinaryForecast:
        event=forecast.prediction
        if event.state!="predicted": raise PredictionRepositoryError("only predicted events may be stored")
        q="""INSERT INTO predictions
        (event_id,entity_id,event_type,model_version,generated_at,occurred_at,probability,
         horizon_seconds,target,evidence_refs,payload)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)
        ON CONFLICT (event_id) DO NOTHING"""
        try:
            with self.connection.cursor() as c:
                c.execute(q,(event.event_id,event.payload["entity_id"],event.event_type,
                    forecast.model_version,event.payload["generated_at"],event.occurred_at,
                    forecast.probability,forecast.horizon.total_seconds(),
                    json.dumps(event.payload["target"]),json.dumps(list(event.evidence_refs)),
                    json.dumps(dict(event.payload))))
            self.connection.commit()
        except Exception as exc:
            try:self.connection.rollback()
            except Exception:pass
            raise PredictionRepositoryError("failed to persist prediction") from exc
        return forecast

    def score(self, event_id:str, probability:float, outcome:int, *, evaluated_at):
        if not 0<=probability<=1 or outcome not in (0,1): raise PredictionRepositoryError("invalid score")
        eps=1e-15; p=min(max(probability,eps),1-eps)
        brier=(p-outcome)**2
        logloss=-(outcome*math.log(p)+(1-outcome)*math.log(1-p))
        q="""INSERT INTO prediction_scores(event_id,outcome,brier_loss,log_loss,evaluated_at)
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (event_id) DO UPDATE SET outcome=EXCLUDED.outcome,
        brier_loss=EXCLUDED.brier_loss,log_loss=EXCLUDED.log_loss,evaluated_at=EXCLUDED.evaluated_at"""
        try:
            with self.connection.cursor() as c:c.execute(q,(event_id,outcome,brier,logloss,evaluated_at))
            self.connection.commit()
        except Exception as exc:
            try:self.connection.rollback()
            except Exception:pass
            raise PredictionRepositoryError("failed to persist prediction score") from exc
        return {"event_id":event_id,"brier_loss":brier,"log_loss":logloss}
