"""Typed Korean presentation for immutable activity observations."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final
from urllib.parse import urlencode

from fastapi import Request

from codex_ticket_dashboard.storage.lifecycle_queries import (
    Activity,
    ActivityPage,
    ActivityPageRequest,
)

_KST: Final = timezone(timedelta(hours=9))
_FILTERS: Final = ("source_host", "thread_id", "turn_id", "parent_thread_id", "ticket_id")
_EVENTS: Final = {
    "THREAD_OBSERVED": "작업 관측",
    "USER_FEEDBACK_OBSERVED": "사용자 입력 관측",
    "SUBAGENT_STARTED": "하위 작업 시작 관측",
    "SUBAGENT_STOPPED": "하위 작업 정지 관측",
    "TURN_STOPPED": "응답 정지 관측",
    "THREAD_OBSERVATION_ENDED": "작업 관측 종료",
}
_MISSING: Final = {
    "PREFLIGHT": "작업 전 확인",
    "TURN_SUMMARY": "응답 요약",
    "GIT_GATE": "Git 확인",
    "WIKI_GATE": "Wiki 기록 확인",
    "MCP_UNAVAILABLE": "기록 도구 연결",
    "PENDING_INGEST": "수집 반영",
    "IDENTITY_UNVERIFIED": "작업 식별 확인",
    "POLICY_DECLARATION_MISMATCH": "작업 선언과 적용 정책 불일치",
}
_RESOLUTION: Final = {"RESOLVED": "식별됨", "UNCLASSIFIED": "미분류", "CONFLICT": "식별 충돌"}


@dataclass(frozen=True, slots=True)
class ActivityCard:
    """Keep observation facts separate from Korean explanations and ticket decisions."""

    item: Activity

    @property
    def title(self) -> str:
        """Describe only the lifecycle observation, never business completion."""
        return _EVENTS.get(self.item.event_type, "활동 관측")

    @property
    def record_label(self) -> str:
        """Distinguish ingestion waiting from missing required business records."""
        if set(self.item.effective_missing_requirements) == {"PENDING_INGEST"}:
            return "수집 대기"
        return {
            "RECORDED": "연결 기록 확인",
            "MISSING": "필수 기록 누락",
            "UNVERIFIED": "기록 확인 전",
        }[self.item.semantic_state]

    @property
    def next_action(self) -> str:
        """Give bounded follow-up without implying automatic retry or acceptance."""
        if "POLICY_DECLARATION_MISMATCH" in self.item.effective_missing_requirements:
            return "작업 전 선언한 Git·Wiki 요구사항을 적용 정책과 대조하십시오."
        if "PENDING_INGEST" in self.item.effective_missing_requirements:
            return "수집 상태를 확인한 뒤 최신 기록을 다시 조회하십시오."
        return {
            "MISSING": "누락된 기록을 확인하고 해당 작업에서 보완하십시오.",
            "UNVERIFIED": "작업 식별과 기록 도구 연결을 확인하십시오.",
            "RECORDED": "연결 티켓에서 작업 결과와 사용자 결정을 확인하십시오.",
        }[self.item.semantic_state]

    @property
    def missing_labels(self) -> tuple[str, ...]:
        """Translate the fixed requirement vocabulary without exposing raw logs."""
        return tuple(_MISSING[value] for value in self.item.effective_missing_requirements)

    @property
    def coverage_label(self) -> str:
        """Observed is evidence for this event only, not complete Host coverage."""
        return {
            "UNVERIFIED": "관측 범위 미확인",
            "OBSERVED": "이 사건 관측됨",
            "GAP_DETECTED": "관측 누락 감지",
        }[self.item.coverage]

    @property
    def observed_project(self) -> str:
        """Present immutable original identity independently from later resolution."""
        return self.item.project_id or _RESOLUTION[self.item.project_resolution_state]

    @property
    def effective_project(self) -> str:
        """Present resolution bounded by the requested snapshot."""
        return (
            self.item.effective_project_id
            or _RESOLUTION[self.item.effective_project_resolution_state]
        )

    @property
    def observed_time(self) -> str:
        """Show a verified-offset time in KST, preserving unknown offsets honestly."""
        parsed = datetime.fromisoformat(self.item.observed_at)
        if parsed.tzinfo is None:
            return self.item.observed_at + " (시간대 미확인)"
        return parsed.astimezone(_KST).strftime("%Y-%m-%d %H:%M:%S KST")

    @property
    def relation_label(self) -> str:
        """Avoid asserting a parent-child relationship without verified metadata."""
        return {"VERIFIED": "관계 확인됨", "UNVERIFIED": "관계 미확인", "CONFLICT": "관계 충돌"}[
            self.item.effective_relation_state
        ]

    @property
    def readiness_label(self) -> str:
        """Separate record-tool readiness from successful recorded work."""
        return {"READY": "연결 준비 확인", "UNVERIFIED": "연결 미확인", "UNAVAILABLE": "연결 불가"}[
            self.item.mcp_readiness
        ]


def activity_request(request: Request) -> ActivityPageRequest:
    """Parse only supported exact filters and bounded pagination at the HTTP edge."""
    names = (*_FILTERS, "limit", "after_ingest_seq", "snapshot_high_watermark")
    return ActivityPageRequest.model_validate(
        {key: request.query_params[key] for key in names if request.query_params.get(key)}
    )


def next_activity_url(page: ActivityPage, query: ActivityPageRequest) -> str | None:
    """Preserve all exact filters and the first-page high watermark."""
    if page.next_after_ingest_seq is None:
        return None
    values = query.model_dump(exclude_none=True)
    values.update(
        after_ingest_seq=page.next_after_ingest_seq,
        snapshot_high_watermark=page.snapshot_high_watermark,
    )
    return "/activities?" + urlencode(values)


def activity_page_sizes(query: ActivityPageRequest) -> tuple[tuple[int, str], ...]:
    """Keep exact filters while deliberately starting a fresh page-size snapshot."""
    values = query.model_dump(
        exclude={"limit", "after_ingest_seq", "snapshot_high_watermark"}, exclude_none=True
    )
    return tuple(
        (size, "/activities?" + urlencode({**values, "limit": size})) for size in (50, 100, 200)
    )
