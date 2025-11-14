"""Globale Projekteinstellungen für GralsBot."""

MODEL_NAME = "text-embedding-3-large"
MODEL_SEGMENTATION = "gpt-5.1-pro-reasoning"
MODEL_REVIEW = "gpt-4.1"

PATH_RAW = "backend/data/raw"
PATH_SEGMENTE = "backend/data/segmente"
PATH_INDEX = "backend/data/index.pkl"

SEG_MIN_WORDS = 180
SEG_TARGET_MIN = 200
SEG_TARGET_MAX = 350
SEG_HARD_MAX = 500

TOP_K = 4
INDEX_PATH = PATH_INDEX

__all__ = [
    "MODEL_NAME",
    "MODEL_SEGMENTATION",
    "MODEL_REVIEW",
    "PATH_RAW",
    "PATH_SEGMENTE",
    "PATH_INDEX",
    "SEG_MIN_WORDS",
    "SEG_TARGET_MIN",
    "SEG_TARGET_MAX",
    "SEG_HARD_MAX",
    "TOP_K",
    "INDEX_PATH",
]
