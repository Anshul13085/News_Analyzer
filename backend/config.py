import os

ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_INDEX = os.getenv("ES_INDEX", "news_articles")  # you already created this
DEFAULT_LANG = "en"

# Model names (change later if you want different ones)
SENTIMENT_MODEL = os.getenv("SENTIMENT_MODEL", "cardiffnlp/twitter-xlm-roberta-base-sentiment")
NER_MODEL = os.getenv("NER_MODEL", "Davlan/xlm-roberta-base-ner-hrl")
BIAS_MODEL = os.getenv("BIAS_MODEL", "joeddav/xlm-roberta-large-xnli")

# Summarizer: good English baseline; multilingual options are heavier/slow
SUMMARIZER_MODEL = os.getenv("SUMMARIZER_MODEL", "sshleifer/distilbart-cnn-12-6")
MAX_SUMMARY_TOKENS = int(os.getenv("MAX_SUMMARY_TOKENS", "160"))
