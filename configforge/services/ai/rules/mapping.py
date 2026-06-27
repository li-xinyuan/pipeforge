"""规则引擎：列映射推荐。

从 api/ai.py 抽取，基于名称匹配启发式（同义词/缩写/子串）推荐源列到目标列的映射。
"""

# Common synonyms/abbreviations (CN-EN, abbreviations)
_SYNONYMS = {
    "name": ["名称", "名字", "姓名", "nm"],
    "id": ["编号", "标识", "identifier"],
    "email": ["邮箱", "电子邮件", "mail", "e-mail"],
    "phone": ["电话", "手机", "mobile", "tel", "telephone"],
    "address": ["地址", "addr"],
    "age": ["年龄", "岁数"],
    "gender": ["性别", "sex"],
    "date": ["日期", "时间", "time", "created_at", "updated_at"],
    "amount": ["金额", "数量", "money", "price", "total"],
    "status": ["状态", "state"],
    "type": ["类型", "category", "kind"],
    "city": ["城市", "town"],
    "country": ["国家", "nation"],
    "company": ["公司", "企业", "org", "organization"],
    "description": ["描述", "说明", "desc", "remark", "备注"],
}


def _build_synonym_lookup() -> dict[str, str]:
    """Build reverse lookup: synonym → canonical."""
    lookup: dict[str, str] = {}
    for canonical, syns in _SYNONYMS.items():
        for syn in syns:
            lookup[syn.lower()] = canonical
        lookup[canonical] = canonical
    return lookup


_SYNONYM_TO_CANONICAL = _build_synonym_lookup()


def _normalize(s: str) -> str:
    """Normalize column name: lowercase, remove underscores/spacing."""
    return s.lower().replace("_", "").replace("-", "").replace(" ", "").strip()


def mapping_suggestions(source_columns: list[str], target_columns: list[str]) -> list[dict]:
    """Rule-based column mapping using name matching heuristics.

    Returns list of {source, target, confidence, reason} dicts.
    """
    suggestions: list[dict] = []
    used_targets: set[str] = set()

    # First pass: exact matches and synonym matches
    for src in source_columns:
        src_norm = _normalize(src)
        src_canonical = _SYNONYM_TO_CANONICAL.get(src_norm, src_norm)

        best_target = None
        best_confidence = 0.0
        best_reason = ""

        for tgt in target_columns:
            if tgt in used_targets:
                continue
            tgt_norm = _normalize(tgt)
            tgt_canonical = _SYNONYM_TO_CANONICAL.get(tgt_norm, tgt_norm)

            if src_norm == tgt_norm:
                best_target = tgt
                best_confidence = 1.0
                best_reason = "名称完全匹配"
                break
            elif src_canonical == tgt_canonical and (
                src_canonical != src_norm or tgt_canonical != tgt_norm
            ):
                # At least one side is a non-canonical synonym → synonym match
                best_target = tgt
                best_confidence = 0.9
                best_reason = "同义词匹配"
                break
            elif src_canonical == tgt_canonical:
                best_target = tgt
                best_confidence = 0.85
                best_reason = "规范化后匹配"

        if best_target:
            suggestions.append({
                "source": src,
                "target": best_target,
                "confidence": best_confidence,
                "reason": best_reason,
            })
            used_targets.add(best_target)

    # Second pass: fuzzy substring matching for unmatched sources
    for src in source_columns:
        if any(s["source"] == src for s in suggestions):
            continue
        src_norm = _normalize(src)

        best_target = None
        best_confidence = 0.0
        for tgt in target_columns:
            if tgt in used_targets:
                continue
            tgt_norm = _normalize(tgt)
            # Substring match
            if src_norm and tgt_norm and (src_norm in tgt_norm or tgt_norm in src_norm):
                confidence = 0.6
                if confidence > best_confidence:
                    best_target = tgt
                    best_confidence = confidence

        if best_target:
            suggestions.append({
                "source": src,
                "target": best_target,
                "confidence": best_confidence,
                "reason": "子串匹配",
            })
            used_targets.add(best_target)

    return suggestions
