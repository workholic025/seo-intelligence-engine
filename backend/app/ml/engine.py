from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session
from xgboost import XGBClassifier

from app.models.models import Backlink, CrawledPage, MlPrediction, MlTrainingLabel, ModelVersion

ARTIFACT_DIR = Path("/app/ml_models")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
MIN_HUMAN_LABELS = 20


def _extract_backlink_feature_vector(bl: Backlink, domain_bl_count: int, unique_sources: int) -> list[float]:
    anchor = (bl.anchor_text or "").strip()
    anchor_len = float(len(anchor))
    is_empty_anchor = 1.0 if not anchor else 0.0
    is_dofollow = 1.0 if bl.is_dofollow else 0.0
    has_context = 1.0 if (bl.placement_context and len(bl.placement_context) > 30) else 0.0
    concentration = float(domain_bl_count) / float(max(1, unique_sources))
    http_ok = 1.0 if bl.source_http_status == 200 else 0.0
    return [anchor_len, is_empty_anchor, is_dofollow, has_context, concentration, http_ok]


def train_spam_classifier_from_human_labels(db: Session) -> dict:
    """
    Trains a CPU Random Forest model ONLY on human-reviewed labels in `ml_training_labels`.
    Never fabricates labels.
    """
    labels = db.query(MlTrainingLabel).all()
    if len(labels) < MIN_HUMAN_LABELS:
        return {
            "trained": False,
            "reason": f"Insufficient human-reviewed labels ({len(labels)}/{MIN_HUMAN_LABELS}). Rule-based analysis remains active.",
        }

    X_rows, y_rows = [], []
    for lbl in labels:
        bl = db.query(Backlink).filter(Backlink.id == lbl.backlink_id).first()
        if not bl:
            continue
        dom_cnt = db.query(Backlink).filter(Backlink.target_domain == bl.target_domain).count()
        uniq_src = db.query(Backlink.source_domain).filter(Backlink.target_domain == bl.target_domain).distinct().count()
        X_rows.append(_extract_backlink_feature_vector(bl, dom_cnt, uniq_src))
        y_rows.append(1 if lbl.is_spam else 0)

    if len(set(y_rows)) < 2:
        return {"trained": False, "reason": "Training labels must contain both spam and non-spam classes."}

    X = np.array(X_rows, dtype=np.float32)
    y = np.array(y_rows, dtype=np.int32)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, n_jobs=2)
    rf.fit(X_train, y_train)
    rf_preds = rf.predict(X_test)
    rf_f1 = float(f1_score(y_test, rf_preds, zero_division=0))

    xgb = XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42,
                        eval_metric="logloss", verbosity=0, n_jobs=2)
    xgb.fit(X_train, y_train)
    xgb_preds = xgb.predict(X_test)
    xgb_f1 = float(f1_score(y_test, xgb_preds, zero_division=0))

    # Pick the model with the higher F1 on the hold-out set
    if xgb_f1 >= rf_f1:
        clf, preds, model_type = xgb, xgb_preds, "xgb"
    else:
        clf, preds, model_type = rf, rf_preds, "rf"

    metrics = {
        "model_type": model_type,
        "precision": round(float(precision_score(y_test, preds, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, preds, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_test, preds, zero_division=0)), 4),
        "rf_f1": round(rf_f1, 4),
        "xgb_f1": round(xgb_f1, 4),
        "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
        "train_samples": int(len(y_train)),
        "test_samples": int(len(y_test)),
    }

    version_tag = f"{model_type}-spam-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    artifact_path = str(ARTIFACT_DIR / f"{version_tag}.joblib")
    joblib.dump(clf, artifact_path)

    db.query(ModelVersion).filter(ModelVersion.model_name == "spam_rf").update({"is_active": False})
    db.add(ModelVersion(model_name="spam_rf", version_tag=version_tag, artifact_path=artifact_path, metrics_json=metrics, is_active=True))
    db.commit()

    return {"trained": True, "version_tag": version_tag, "metrics": metrics}


def run_spam_and_anomaly_analysis(db: Session, domain: str) -> dict:
    """Runs ML/rule-based spam risk analysis + Isolation Forest anomaly detection."""
    clean = domain.removeprefix("www.").lower().strip()
    backlinks = db.query(Backlink).filter(Backlink.target_domain == clean).limit(500).all()

    if not backlinks:
        return {
            "domain": clean,
            "ml_status": "insufficient_data",
            "model_version": "none",
            "risk_category": "unassessed",
            "risk_probability": None,
            "anomaly_detected": False,
            "supporting_indicators": [],
        }

    unique_sources = len({b.source_domain for b in backlinks})
    dom_cnt = len(backlinks)
    X = np.array([_extract_backlink_feature_vector(b, dom_cnt, unique_sources) for b in backlinks], dtype=np.float32)

    # Rule-based risk indicators (always computed as transparent evidence)
    indicators = []
    concentration = dom_cnt / max(1, unique_sources)
    dofollow_ratio = sum(1 for b in backlinks if b.is_dofollow) / dom_cnt
    empty_ratio = sum(1 for b in backlinks if not (b.anchor_text or "").strip()) / dom_cnt

    rule_score = 0.0
    if concentration > 10.0:
        rule_score += 0.35
        indicators.append(f"High link concentration ({concentration:.1f} backlinks per referring domain).")
    if dofollow_ratio > 0.95 and dom_cnt >= 20:
        rule_score += 0.25
        indicators.append(f"Unusually high DoFollow ratio ({dofollow_ratio*100:.1f}%).")
    if empty_ratio > 0.60:
        rule_score += 0.15
        indicators.append(f"Large share of empty anchors ({empty_ratio*100:.1f}%).")

    # Check if a validated human-labeled RF model exists
    active_model = (
        db.query(ModelVersion)
        .filter(ModelVersion.model_name == "spam_rf", ModelVersion.is_active.is_(True))
        .order_by(ModelVersion.trained_at.desc())
        .first()
    )

    ml_available = False
    model_version = "rule-based-v1 (ML model unavailable: insufficient human labels)"
    avg_prob = round(min(1.0, rule_score), 4)

    if active_model and Path(active_model.artifact_path).exists():
        clf = joblib.load(active_model.artifact_path)
        probs = clf.predict_proba(X)[:, 1]
        avg_prob = round(float(np.mean(probs)), 4)
        model_version = active_model.version_tag
        ml_available = True

    # Isolation Forest Anomaly Detection (unsupervised, needs >= 10 records)
    anomaly_flag = False
    anomaly_count = 0
    if len(X) >= 10:
        iso = IsolationForest(contamination=0.1, random_state=42, n_jobs=1)
        iso_preds = iso.fit_predict(X)
        anomaly_count = int(np.sum(iso_preds == -1))
        if anomaly_count / len(X) > 0.15:
            anomaly_flag = True
            indicators.append(f"Isolation Forest flagged {anomaly_count} anomalous link records.")

    risk_cat = "high_risk" if avg_prob >= 0.65 else "moderate_risk" if avg_prob >= 0.35 else "low_risk"

    db.add(
        MlPrediction(
            domain=clean,
            model_version=model_version,
            spam_probability=avg_prob,
            risk_category=risk_cat,
            anomaly_flag=anomaly_flag,
            supporting_indicators=indicators,
        )
    )
    db.commit()

    return {
        "domain": clean,
        "ml_model_available": ml_available,
        "model_version": model_version,
        "risk_probability": avg_prob,
        "risk_category": risk_cat,
        "anomaly_detected": anomaly_flag,
        "anomalous_links_count": anomaly_count,
        "supporting_indicators": indicators,
        "disclaimer": "Risk assessment indicators only; unvalidated predictions are not confirmed spam.",
    }


def compute_content_relevance(db: Session, source_url: str, target_domain: str) -> dict:
    """TF-IDF + Cosine Similarity between source page excerpt and target domain indexed pages."""
    src_page = db.query(CrawledPage).filter(CrawledPage.url == source_url).first()
    tgt_pages = db.query(CrawledPage.text_excerpt).filter(CrawledPage.domain == target_domain.lower()).limit(10).all()

    if not src_page or not src_page.text_excerpt or not tgt_pages:
        return {"relevance_score": None, "status": "insufficient_content", "top_shared_terms": []}

    target_corpus = " ".join(p[0] for p in tgt_pages if p[0])
    if not target_corpus.strip():
        return {"relevance_score": None, "status": "insufficient_content", "top_shared_terms": []}

    vec = TfidfVectorizer(stop_words="english", max_features=500)
    tfidf = vec.fit_transform([src_page.text_excerpt, target_corpus])
    sim = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])

    # Identify top contributing shared terms
    feature_names = np.array(vec.get_feature_names_out())
    product = (tfidf[0].toarray()[0] * tfidf[1].toarray()[0])
    top_idx = np.argsort(product)[::-1][:8]
    shared_terms = [str(feature_names[i]) for i in top_idx if product[i] > 0]

    return {
        "relevance_score": round(sim, 4),
        "top_shared_terms": shared_terms,
        "evidence": f"Computed via TF-IDF cosine similarity across {len(tgt_pages)} indexed target pages.",
    }


def cluster_indexed_domains(db: Session, n_clusters: int = 5) -> dict:
    """K-Means topical clustering of indexed domains using TF-IDF page content."""
    pages = db.query(CrawledPage.domain, CrawledPage.text_excerpt).filter(CrawledPage.text_excerpt != "").limit(1000).all()
    if not pages:
        return {"clusters": [], "status": "insufficient_data"}

    df = pd.DataFrame(pages, columns=["domain", "text"]).groupby("domain")["text"].apply(" ".join).reset_index()
    k = min(n_clusters, len(df))
    if k < 2:
        return {"clusters": [{"cluster_id": 0, "domains": df["domain"].tolist()}], "status": "single_cluster"}

    vec = TfidfVectorizer(stop_words="english", max_features=300)
    X = vec.fit_transform(df["text"])
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    df["cluster"] = km.fit_predict(X)

    clusters = []
    for cid, grp in df.groupby("cluster"):
        clusters.append({"cluster_id": int(cid), "domain_count": len(grp), "domains": grp["domain"].tolist()[:30]})
    return {"clusters": clusters, "total_clustered_domains": len(df)}