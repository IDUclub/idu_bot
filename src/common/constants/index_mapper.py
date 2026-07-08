# Test RAG index that stores docx text chunks together with a geojson layer
# (isochrone). The layer is returned only when a geojson-bearing chunk is
# retrieved. Managed through the dedicated /llm/test/transport endpoints.
TEST_TRANSPORT_INDEX = "test_transport"

index_mapper = {
    "general": "Общее",
    "investment": "Инвестиционная стадия",
    "pre_design": "Предпроектная стадия",
    "design": "Проектная стадия",
    "construction": "Строительная стадия",
    "operation": "Эксплуатационная стадия",
    "decommission": "Ликвидационная стадия",
    TEST_TRANSPORT_INDEX: "Транспорт (тест)",
    # "project": "Информация проекта",
    # "project_2": "Общее о проекте",
    # "project_120": "Информация о проекте",
    # "pzz": "ПЗЗ",
    # "Moscow&": "Информация о проекте Город-Сад",
}

reverse_index_mapper = {v: k for k, v in index_mapper.items()}
