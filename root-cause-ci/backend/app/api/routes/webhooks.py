from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import verify_webhook_signature
from app.core.database import get_db_session
from app.models.webhook_event import WebhookEvent
from app.schemas.ingestion import WebhookIngestionResponse
from app.services.ingestion.github_actions import GitHubActionsIngestionService, get_github_actions_ingestion_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github", response_model=WebhookIngestionResponse)
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(default=None, alias="X-GitHub-Event"),
    x_github_delivery: str | None = Header(default=None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db_session),
    ingestion_service: GitHubActionsIngestionService = Depends(get_github_actions_ingestion_service),
) -> WebhookIngestionResponse:
    payload_bytes = await request.body()
    if settings.github_webhook_secret:
        if not verify_webhook_signature(payload_bytes, x_hub_signature_256, settings.github_webhook_secret):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid GitHub webhook signature")

    payload = await request.json()
    if x_github_event not in {"workflow_run", "workflow_job"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported GitHub event type")

    if not x_github_delivery:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing GitHub delivery ID")

    existing_event = db.scalar(
        select(WebhookEvent).where(WebhookEvent.delivery_id == x_github_delivery)
    )
    if existing_event:
        stored_response = json.loads(existing_event.result)
        return WebhookIngestionResponse.model_validate(stored_response)

    ingestion_result = ingestion_service.ingest_event(
        event_type=x_github_event,
        delivery_id=x_github_delivery,
        payload=payload,
    )
    response = WebhookIngestionResponse(
        status="accepted",
        delivery_id=x_github_delivery,
        event_type=x_github_event,
        ingestion=ingestion_result,
    )
    db.add(
        WebhookEvent(
            delivery_id=x_github_delivery,
            event_type=x_github_event,
            payload=payload_bytes.decode("utf-8"),
            result=json.dumps(response.model_dump(mode="json")),
        )
    )
    db.commit()
    return response
