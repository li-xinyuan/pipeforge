"""Data models for notification configs and history."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NotificationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    type: Literal["webhook", "email"] = "webhook"
    enabled: bool = True

    # Webhook config
    webhook_url: str = ""
    webhook_provider: Literal["dingtalk", "wecom", "feishu", "generic"] = "generic"
    webhook_headers: dict[str, str] = Field(default_factory=dict)

    # Email config (Phase 3B-05)
    email_to: list[str] = Field(default_factory=list)
    email_subject_template: str = ""
    email_body_template: str = ""

    # Custom message template (T-5D-04). Empty = use default formatter.
    # Supports variables: {{config_name}}, {{status}}, {{duration}}, {{rows}}, {{error}}, etc.
    message_template: str = ""

    # Trigger conditions
    trigger_on_success: bool = True
    trigger_on_failure: bool = True
    trigger_on_anomaly: bool = False

    # Associated configs (None = all configs)
    config_ids: list[str] | None = None


class NotificationConfigCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    type: Literal["webhook", "email"] = "webhook"
    enabled: bool = True

    # Webhook
    webhook_url: str = ""
    webhook_provider: Literal["dingtalk", "wecom", "feishu", "generic"] = "generic"
    webhook_headers: dict[str, str] = Field(default_factory=dict)

    # Email
    email_to: list[str] = Field(default_factory=list)
    email_subject_template: str = ""
    email_body_template: str = ""

    # Custom message template
    message_template: str = ""

    # Trigger
    trigger_on_success: bool = True
    trigger_on_failure: bool = True
    trigger_on_anomaly: bool = False

    # Associated configs
    config_ids: list[str] | None = None


class NotificationConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None

    # Webhook
    webhook_url: str | None = None
    webhook_provider: Literal["dingtalk", "wecom", "feishu", "generic"] | None = None
    webhook_headers: dict[str, str] | None = None

    # Email
    email_to: list[str] | None = None
    email_subject_template: str | None = None
    email_body_template: str | None = None

    # Custom message template
    message_template: str | None = None

    # Trigger
    trigger_on_success: bool | None = None
    trigger_on_failure: bool | None = None
    trigger_on_anomaly: bool | None = None

    # Associated configs
    config_ids: list[str] | None = None


class NotificationHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    config_id: str  # notification config id
    config_name: str  # notification config name
    execution_id: str
    pipeline_config_name: str
    status: str  # success / failed
    notify_success: bool
    provider: str
    message: str
    triggered_at: str
