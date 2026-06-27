from __future__ import annotations

import re

from .base import NotifyContext


def _status_display(status: str) -> tuple[str, str]:
    """Return (icon, label) for a given status."""
    if status == "success":
        return "✅", "成功"
    elif status == "anomaly":
        return "⚠️", "异常"
    else:
        return "❌", "失败"


def _format_duration(seconds: float | None) -> str:
    """Format duration in seconds to a human-readable string."""
    if seconds is None:
        return "-"
    if seconds < 1:
        return f"{int(seconds * 1000)}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m{secs:.0f}s"


def _format_rows(row_count: int | None) -> str:
    """Format row count to a human-readable string."""
    if row_count is None:
        return "-"
    return f"{row_count:,}"


# Template variable pattern: {{variable_name}}
_TEMPLATE_VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def get_template_variables() -> list[str]:
    """Return the list of supported template variables."""
    return [
        "config_name", "status", "summary", "duration", "rows",
        "error", "error_type", "stack_summary", "output_files", "started_at", "finished_at",
        "execution_id",
    ]


def render_template(template: str, context: NotifyContext) -> str:
    """Render a notification template by replacing {{variable}} placeholders.

    Supported variables:
      - {{config_name}}: Pipeline configuration name
      - {{status}}: Execution status (success/failed/anomaly)
      - {{summary}}: Execution summary
      - {{duration}}: Formatted duration (e.g. "1.5s", "2m30s")
      - {{rows}}: Row count (e.g. "1,234")
      - {{error}}: Error message (if any)
      - {{error_type}}: Error type (if any)
      - {{stack_summary}}: Error stack trace summary (if any)
      - {{output_files}}: Comma-separated list of output files
      - {{started_at}}: Execution start time
      - {{finished_at}}: Execution finish time
      - {{execution_id}}: Execution ID
    """
    def _replace(match: re.Match) -> str:
        var = match.group(1)
        if var == "config_name":
            return context.config_name
        elif var == "status":
            return context.status
        elif var == "summary":
            return context.summary
        elif var == "duration":
            return _format_duration(context.duration_seconds)
        elif var == "rows":
            return _format_rows(context.row_count)
        elif var == "error":
            return context.error_message or ""
        elif var == "error_type":
            return context.error_type or ""
        elif var == "stack_summary":
            return context.stack_summary or ""
        elif var == "output_files":
            return ", ".join(context.output_files)
        elif var == "started_at":
            return context.started_at
        elif var == "finished_at":
            return context.finished_at
        elif var == "execution_id":
            return context.execution_id
        # Unknown variable — leave as-is
        return match.group(0)

    return _TEMPLATE_VAR_RE.sub(_replace, template)


def format_dingtalk(context: NotifyContext) -> dict:
    """Format notification for DingTalk robot (markdown message)."""
    icon, label = _status_display(context.status)
    title = f"{icon} ConfigForge 执行{label}"
    lines = [
        f"### {title}",
        f"**配置**: {context.config_name}",
        f"**状态**: {context.status}",
        f"**摘要**: {context.summary}",
    ]
    if context.duration_seconds is not None:
        lines.append(f"**耗时**: {_format_duration(context.duration_seconds)}")
    if context.row_count is not None:
        lines.append(f"**行数**: {_format_rows(context.row_count)}")
    if context.output_files:
        lines.append(f"**输出文件**: {', '.join(context.output_files)}")
    if context.error_message:
        lines.append(f"**错误信息**: {context.error_message}")
    if context.error_type:
        lines.append(f"**错误类型**: {context.error_type}")
    if context.stack_summary:
        lines.append(f"**堆栈摘要**: {context.stack_summary}")
    lines.append(f"**开始时间**: {context.started_at}")
    lines.append(f"**完成时间**: {context.finished_at}")

    return {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": "\n\n".join(lines),
        },
    }


def format_wecom(context: NotifyContext) -> dict:
    """Format notification for WeCom (WeChat Work) robot (markdown message)."""
    icon, label = _status_display(context.status)
    color = "info" if context.status == "success" else ("warning" if context.status == "anomaly" else "comment")
    lines = [
        f"### {icon} ConfigForge 执行{label}",
        f"> 配置: <font color=\"info\">{context.config_name}</font>",
        f"> 状态: <font color=\"{color}\">{context.status}</font>",
        f"> 摘要: {context.summary}",
    ]
    if context.duration_seconds is not None:
        lines.append(f"> 耗时: {_format_duration(context.duration_seconds)}")
    if context.row_count is not None:
        lines.append(f"> 行数: {_format_rows(context.row_count)}")
    if context.output_files:
        lines.append(f"> 输出文件: {', '.join(context.output_files)}")
    if context.error_message:
        lines.append(f"> 错误信息: <font color=\"warning\">{context.error_message}</font>")
    if context.error_type:
        lines.append(f"> 错误类型: {context.error_type}")
    if context.stack_summary:
        lines.append(f"> 堆栈: {context.stack_summary}")
    lines.append(f"> 开始: {context.started_at}  完成: {context.finished_at}")

    return {
        "msgtype": "markdown",
        "markdown": {
            "content": "\n".join(lines),
        },
    }


def format_feishu(context: NotifyContext) -> dict:
    """Format notification for Feishu (Lark) robot (interactive card)."""
    if context.status == "success":
        status_color, status_text = "green", "成功"
    elif context.status == "anomaly":
        status_color, status_text = "orange", "异常"
    else:
        status_color, status_text = "red", "失败"

    elements = [
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**配置**: {context.config_name}"},
        },
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**摘要**: {context.summary}"},
        },
    ]
    if context.duration_seconds is not None:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**耗时**: {_format_duration(context.duration_seconds)}"},
        })
    if context.row_count is not None:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**行数**: {_format_rows(context.row_count)}"},
        })
    if context.output_files:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**输出文件**: {', '.join(context.output_files)}"},
        })
    if context.error_message:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**错误**: {context.error_message}"},
        })
    if context.error_type:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**错误类型**: {context.error_type}"},
        })
    if context.stack_summary:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**堆栈摘要**: {context.stack_summary}"},
        })
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": f"开始: {context.started_at}  完成: {context.finished_at}"},
    })

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"ConfigForge 执行{status_text}",
                },
                "template": status_color,
            },
            "elements": elements,
        },
    }


def format_generic(context: NotifyContext) -> dict:
    """Format notification as generic JSON."""
    payload: dict = {
        "execution_id": context.execution_id,
        "config_name": context.config_name,
        "status": context.status,
        "summary": context.summary,
        "started_at": context.started_at,
        "finished_at": context.finished_at,
    }
    if context.duration_seconds is not None:
        payload["duration_seconds"] = context.duration_seconds
    if context.row_count is not None:
        payload["row_count"] = context.row_count
    if context.output_files:
        payload["output_files"] = context.output_files
    if context.error_message:
        payload["error_message"] = context.error_message
    if context.error_type:
        payload["error_type"] = context.error_type
    if context.stack_summary:
        payload["stack_summary"] = context.stack_summary
    return payload
