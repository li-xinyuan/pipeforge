ERROR_MESSAGES = {
    "FILE_FORMAT_UNSUPPORTED": "文件格式不支持，请上传 .xlsx 或 .csv 格式的文件",
    "FILE_TOO_LARGE": "文件过大，最大支持 50MB",
    "VALIDATION_ERROR": "输入数据格式不正确，请检查后重试",
    "SQL_EXECUTION_ERROR": "SQL 执行失败，请检查 SQL 语法和列名拼写",
    "PATH_TRAVERSAL": "非法的文件访问路径",
    "DDL_DML_NOT_ALLOWED": "不允许执行 DDL/DML 语句，仅支持 SELECT 查询",
    "AI_TIMEOUT": "AI 响应超时，请稍后重试",
    "AI_CALL_FAILED": "AI 调用失败，请稍后重试",
    "AI_KEY_INVALID": "API Key 无效，请检查设置",
    "AI_DISABLED": "AI 未配置，请先在设置中启用",
    "CONNECTION_FAILED": "连接失败，请检查网络和设置",
    "PIPELINE_FAILED": "流水线执行失败，请检查配置",
}


def get_user_message(code: str, fallback: str = "操作失败，请稍后重试") -> str:
    return ERROR_MESSAGES.get(code, fallback)
