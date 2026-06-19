from __future__ import annotations

from .base import NotifyContext


def _status_display(status: str) -> tuple[str, str]:
    """Return (icon, label) for a given status."""
    if status == "success":
        return "✅", "成功"
    elif status == "anomaly":
        return "⚠️", "异常"
    else:
        return "❌", "失败"


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
    if context.output_files:
        lines.append(f"**输出文件**: {', '.join(context.output_files)}")
    if context.error_message:
        lines.append(f"**错误信息**: {context.error_message}")
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
    if context.output_files:
        lines.append(f"> 输出文件: {', '.join(context.output_files)}")
    if context.error_message:
        lines.append(f"> 错误信息: <font color=\"warning\">{context.error_message}</font>")
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
    if context.output_files:
        payload["output_files"] = context.output_files
    if context.error_message:
        payload["error_message"] = context.error_message
    return payload
