def test_error_messages_known_code():
    from configforge.utils.error_messages import get_user_message
    msg = get_user_message("FILE_FORMAT_UNSUPPORTED")
    assert "不支持" in msg
    assert "xlsx" in msg


def test_error_messages_unknown_code_falls_back():
    from configforge.utils.error_messages import get_user_message
    msg = get_user_message("NONEXISTENT_CODE")
    assert "失败" in msg


def test_error_messages_custom_fallback():
    from configforge.utils.error_messages import get_user_message
    msg = get_user_message("NONEXISTENT", "自定义错误")
    assert msg == "自定义错误"
