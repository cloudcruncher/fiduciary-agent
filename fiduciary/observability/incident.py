import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fiduciary.storage.db import get_connection

logger = logging.getLogger(__name__)


class IncidentSeverity:
    CRITICAL = "CRITICAL"  # Sev 1: Service down, all providers unreachable, DB corrupt
    HIGH = "HIGH"          # Sev 2: Adversarial injection attack, unrepairable invariant violation
    MEDIUM = "MEDIUM"      # Sev 3: Gateway timeout fallback to local, BoE web tool scrape failure
    LOW = "LOW"            # Sev 4: Grounding discrepancy detected and auto-repaired, non-blocking warning


class IncidentEventType:
    SERVICE_OUTAGE = "SERVICE_OUTAGE"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    INVARIANT_BREACH = "INVARIANT_BREACH"
    TOOL_FAILURE = "TOOL_FAILURE"
    FALLBACK_TRIGGERED = "FALLBACK_TRIGGERED"
    UNGROUNDED_REPAIRED = "UNGROUNDED_REPAIRED"


def record_incident(
    severity: str,
    event_type: str,
    service: str,
    summary: str,
    details: Optional[Dict[str, Any]] = None,
    status: str = "OPEN",
) -> Dict[str, Any]:
    """
    Records an enterprise incident alert into the database and generates
    structured logging compatible with Splunk / Datadog / PagerDuty.
    """
    incident_id = f"inc_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now().isoformat()
    details_dict = details or {}
    details_json = json.dumps(details_dict)

    # Structured log output
    log_msg = (
        f"[INCIDENT {severity}] {event_type} on {service}: {summary} | "
        f"id={incident_id} details={details_json}"
    )
    if severity == IncidentSeverity.CRITICAL:
        logger.critical(log_msg)
    elif severity == IncidentSeverity.HIGH:
        logger.error(log_msg)
    elif severity == IncidentSeverity.MEDIUM:
        logger.warning(log_msg)
    else:
        logger.info(log_msg)

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO system_incidents (
                id, timestamp, severity, event_type, service, summary, details_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident_id,
                now_iso,
                severity,
                event_type,
                service,
                summary,
                details_json,
                status,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to record incident {incident_id} to database: {e}")

    return {
        "id": incident_id,
        "timestamp": now_iso,
        "severity": severity,
        "event_type": event_type,
        "service": service,
        "summary": summary,
        "details": details_dict,
        "status": status,
    }


def get_incidents(
    limit: int = 50,
    severity: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieves recent incidents filtered by severity or status."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM system_incidents"
        conditions = []
        params = []

        if severity:
            conditions.append("severity = ?")
            params.append(severity.upper())
        if status:
            conditions.append("status = ?")
            params.append(status.upper())

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, tuple(params))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        for r in rows:
            try:
                r["details"] = json.loads(r.get("details_json") or "{}")
            except Exception:
                r["details"] = {}
        return rows
    except Exception:
        return []


def resolve_incident(incident_id: str, resolution_note: str = "") -> bool:
    """Marks an active incident as RESOLVED."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now_iso = datetime.now().isoformat()
        cursor.execute(
            """
            UPDATE system_incidents
            SET status = 'RESOLVED', resolved_at = ?
            WHERE id = ?
            """,
            (now_iso, incident_id),
        )
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    except Exception:
        return False


def export_traces_splunk(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Transforms recent LLM traces into Splunk HTTP Event Collector (HEC) /
    Elastic Common Schema (ECS) standard JSON format.
    """
    from fiduciary.observability.tracer import get_recent_traces

    traces = get_recent_traces(limit=limit)
    splunk_events = []
    host = os.uname().nodename if hasattr(os, "uname") else "fiduciary-host"

    for t in traces:
        ts_str = t.get("timestamp") or datetime.now().isoformat()
        try:
            epoch = datetime.fromisoformat(ts_str).timestamp()
        except Exception:
            epoch = datetime.now().timestamp()

        event_payload = {
            "@timestamp": ts_str,
            "log.level": "WARN" if t.get("grounding_status") == "UNVERIFIED_FIGURES_DETECTED" else "INFO",
            "trace.id": t.get("id"),
            "service.name": "fiduciary-agent",
            "event.action": "llm_completion",
            "event.duration_ms": t.get("latency_ms", 0.0),
            "ai.caller": t.get("caller", "copilot"),
            "ai.provider": t.get("provider", "local"),
            "ai.model": t.get("model", "unknown"),
            "ai.grounding_status": t.get("grounding_status", "UNKNOWN"),
            "ai.grounding_score": t.get("grounding_score", 1.0),
            "ai.unverified_figures": t.get("unverified_figures", []),
            "ai.tools_count": len(t.get("tools_used", [])),
            "ai.tools_used": t.get("tools_used", []),
        }

        splunk_events.append({
            "time": epoch,
            "host": host,
            "source": "fiduciary:llm_traces",
            "sourcetype": "_json",
            "event": event_payload,
        })

    return splunk_events


def export_incidents_splunk(limit: int = 50) -> List[Dict[str, Any]]:
    """Transforms system incidents into Splunk HEC JSON event format."""
    incidents = get_incidents(limit=limit)
    splunk_events = []
    host = os.uname().nodename if hasattr(os, "uname") else "fiduciary-host"

    for inc in incidents:
        ts_str = inc.get("timestamp") or datetime.now().isoformat()
        try:
            epoch = datetime.fromisoformat(ts_str).timestamp()
        except Exception:
            epoch = datetime.now().timestamp()

        splunk_events.append({
            "time": epoch,
            "host": host,
            "source": "fiduciary:system_incidents",
            "sourcetype": "_json",
            "event": {
                "@timestamp": ts_str,
                "incident.id": inc.get("id"),
                "incident.severity": inc.get("severity"),
                "incident.event_type": inc.get("event_type"),
                "incident.service": inc.get("service"),
                "incident.summary": inc.get("summary"),
                "incident.status": inc.get("status"),
                "incident.details": inc.get("details", {}),
            },
        })

    return splunk_events


def format_pagerduty_payload(
    incident: Dict[str, Any],
    routing_key: str = "PAGERDUTY_INTEGRATION_KEY",
) -> Dict[str, Any]:
    """
    Formats an incident into a PagerDuty Events API v2 trigger payload.
    See: https://developer.pagerduty.com/docs/events-api-v2/trigger-events/
    """
    sev_map = {
        IncidentSeverity.CRITICAL: "critical",
        IncidentSeverity.HIGH: "error",
        IncidentSeverity.MEDIUM: "warning",
        IncidentSeverity.LOW: "info",
    }
    pd_severity = sev_map.get(incident.get("severity", "LOW"), "info")

    return {
        "routing_key": routing_key,
        "event_action": "trigger",
        "dedup_key": incident.get("id"),
        "payload": {
            "summary": f"[{incident.get('severity')}] {incident.get('summary')}",
            "source": f"fiduciary-agent:{incident.get('service', 'core')}",
            "severity": pd_severity,
            "timestamp": incident.get("timestamp"),
            "component": incident.get("service"),
            "group": incident.get("event_type"),
            "custom_details": incident.get("details", {}),
        },
        "links": [
            {
                "href": "http://localhost:8080/architecture.html",
                "text": "Fiduciary Architecture & Incident Runbook",
            }
        ],
    }


def format_slack_alert(incident: Dict[str, Any]) -> Dict[str, Any]:
    """Formats an incident into a Slack Webhook Block Kit notification."""
    color_map = {
        IncidentSeverity.CRITICAL: "#ef4444",  # Red
        IncidentSeverity.HIGH: "#f97316",      # Orange
        IncidentSeverity.MEDIUM: "#eab308",    # Yellow
        IncidentSeverity.LOW: "#10b981",       # Green
    }
    color = color_map.get(incident.get("severity", "LOW"), "#64748b")

    return {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🚨 Fiduciary Alert: [{incident.get('severity')}] {incident.get('event_type')}",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Service:* `{incident.get('service')}`"},
                            {"type": "mrkdwn", "text": f"*Incident ID:* `{incident.get('id')}`"},
                            {"type": "mrkdwn", "text": f"*Status:* `{incident.get('status')}`"},
                            {"type": "mrkdwn", "text": f"*Time:* {incident.get('timestamp')}"},
                        ],
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Summary:*\n{incident.get('summary')}",
                        },
                    },
                ],
            }
        ]
    }
