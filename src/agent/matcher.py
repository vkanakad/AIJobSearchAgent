"""Match jobs to resume using TF-IDF similarity."""
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


def _build_corpus(resume_text: str, jobs: List[Dict]) -> List[str]:
    corpus = [resume_text]
    for j in jobs:
        text = (j.get("title", "") or "") + "\n" + (j.get("description", "") or "")
        corpus.append(text)
    return corpus


def match_jobs(resume_text: str, jobs: List[Dict], top_k: int = 50, threshold: float = 0.12) -> List[Dict]:
    if not jobs:
        return []
    corpus = _build_corpus(resume_text, jobs)
    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    X = vectorizer.fit_transform(corpus)
    resume_vec = X[0:1]
    job_vecs = X[1:]
    sims = cosine_similarity(resume_vec, job_vecs)[0]
    results = []
    for idx, sim in enumerate(sims):
        if sim >= threshold:
            job = jobs[idx].copy()
            job["similarity"] = float(sim)
            results.append(job)
    # sort by similarity descending and take top_k
    results = sorted(results, key=lambda x: x.get("similarity", 0), reverse=True)[:top_k]
    return results
