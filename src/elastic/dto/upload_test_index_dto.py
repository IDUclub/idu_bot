from pydantic import BaseModel, Field

DEFAULT_LAYER_DESCRIPTION = (
    "Слой «15-минутная изохрона автомобильной доступности». Показывает зоны "
    "автомобильной (транспортной) доступности в пределах 15 минут в пути на "
    "автомобиле от рассматриваемой территории и жилых комплексов района. "
    "Изохроны построены на дорожном графе из открытых источников, средняя "
    "скорость движения — около 60 км/ч, кольца изохроны соответствуют разному "
    "времени в пути. Используй этот слой для ответов на вопросы о транспортной "
    "и автомобильной доступности, зоне охвата и времени в пути на автомобиле."
)


class UploadTestIndexDTO(BaseModel):

    doc_name: str = Field(
        default="Транспорт (тест)",
        description="Name of the document to save as property in elasticsearch",
    )
    layer_description: str = Field(
        default=DEFAULT_LAYER_DESCRIPTION,
        description="Text description of the geojson layer used to generate "
        "retrieval questions the layer will be returned for",
    )
    table_context_size: int = Field(
        default=5, examples=[5], description="table context size in paragraphs"
    )
    text_questions_num: int = Field(
        default=10, examples=[10], description="number of text questions"
    )
    table_questions_num: int = Field(
        default=10, examples=[10], description="number of questions for table"
    )
    geojson_questions_num: int = Field(
        default=8,
        examples=[8],
        description="number of retrieval questions generated for the geojson "
        "layer (each becomes a chunk carrying the whole FeatureCollection)",
    )
