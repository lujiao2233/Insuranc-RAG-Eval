from typing import Any


def parse_category_levels(category: str):
    if not category or category == "未分类":
        return "", "", ""
    parts = [part.strip() for part in str(category).split("/") if str(part).strip()]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], ""
    if len(parts) == 1:
        return parts[0], "", ""
    return "", "", ""


def resolve_category_levels_for_export(base_category: str, *metadata_sources: Any) -> tuple[str, str, str]:
    level1, level2, level3 = parse_category_levels(base_category)
    if level3:
        return level1, level2, level3
    for meta in metadata_sources:
        if not isinstance(meta, dict):
            continue
        meta_category = str(meta.get("category_path") or "").strip()
        if meta_category:
            meta_level1, meta_level2, meta_level3 = parse_category_levels(meta_category)
            if meta_level1:
                return meta_level1, meta_level2, meta_level3
    return level1, level2, level3
