from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.core.security import verify_webhook_signature
from app.schemas.ingestion import WebhookIngestionResponse
from app.services.auto_analysis import auto_analyze, should_auto_analyze
from app.services.ingestion.github_actions import GitHubActionsIngestionService, get_github_actions_ingestion_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github", response_model=WebhookIngestionResponse)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str | None = Header(default=None, alias="X-GitHub-Event"),
    x_github_delivery: str | None = Header(default=None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    settings: Settings = Depends(get_settings),
    ingestion_service: GitHubActionsIngestionService = Depends(get_github_actions_ingestion_service),
) -> WebhookIngestionResponse:
    payload_bytes = await request.body()
    if settings.github_webhook_secret:
        if not verify_webhook_signature(payload_bytes, x_hub_signature_256, settings.github_webhook_secret):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid GitHub webhook signature")

    payload = await request.json()
    if x_github_event not in {"workflow_run", "workflow_job"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported GitHub event type")

    ingestion_result = ingestion_service.ingest_event(
        event_type=x_github_event,
        delivery_id=x_github_delivery,
        payload=payload,
    )

    # A completed, failed workflow run is analysed automatically for every linked user.
    target = should_auto_analyze(x_github_event, payload)
    if target:
        background_tasks.add_task(auto_analyze, *target)

    return WebhookIngestionResponse(
        status="accepted",
        delivery_id=x_github_delivery,
        event_type=x_github_event,
        ingestion=ingestion_result,
        auto_analysis_scheduled=bool(target),
    )
