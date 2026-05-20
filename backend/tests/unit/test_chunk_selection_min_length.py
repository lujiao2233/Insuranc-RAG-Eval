from services.advanced_testset_generator import AdvancedTestsetGenerator


def test_filter_chunks_uses_original_content_length():
    generator = AdvancedTestsetGenerator()
    chunks = [
        {
            "chunk": "相关产品：测试产品\n标题",
            "content_length": 2,
            "doc_id": "doc-1",
        },
        {
            "chunk": "相关产品：测试产品\n这是一个足够长的正文片段，用来验证选择阈值过滤逻辑生效。",
            "content_length": 30,
            "doc_id": "doc-1",
        },
    ]

    filtered_chunks, fallback_to_original = generator._filter_chunks_for_generation(
        chunks,
        selection_min_chunk_chars=20,
    )

    assert fallback_to_original is False
    assert len(filtered_chunks) == 1
    assert filtered_chunks[0]["content_length"] == 30
