from utils.category_utils import parse_category_levels, resolve_category_levels_for_export


def test_resolve_category_levels_prefers_metadata_category_path_when_base_has_only_two_levels():
    level1, level2, level3 = resolve_category_levels_for_export(
        "外部制度/法律规章",
        {"category_path": "外部制度/法律规章/风险管理"},
    )

    assert (level1, level2, level3) == ("外部制度", "法律规章", "风险管理")


def test_parse_category_levels_keeps_third_level_for_leaf_category():
    level1, level2, level3 = parse_category_levels("外部制度/法律规章/合规管理")

    assert level1 == "外部制度"
    assert level2 == "法律规章"
    assert level3 == "合规管理"
