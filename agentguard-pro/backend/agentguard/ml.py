"""Tiny trained text classifier (TF-IDF char n-grams + logistic regression). Trains in <1s at import."""
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from .ml_data import build
    from .normalize import clean
    _X, _y = build()
    _MODEL = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, lowercase=True),
                           LogisticRegression(C=4, max_iter=1000, class_weight="balanced")).fit([clean(x) for x in _X], _y)
except Exception:  # sklearn missing: the other layers still work
    _MODEL = None

def available() -> bool: return _MODEL is not None
def prob_injection(text: str) -> float:
    if _MODEL is None: return 0.0
    from .normalize import clean
    return float(_MODEL.predict_proba([clean(text)])[0][1])
