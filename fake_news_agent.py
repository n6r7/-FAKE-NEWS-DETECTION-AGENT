#!/usr/bin/env python3

import re
import requests
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import torch
from transformers import AutoTokenizer, AutoModel
from gnews import GNews

NEWS_API_KEY = "5ae42c64cf0f4f38acab95cde2c276be"

NEWS_ENDPOINT = "https://newsapi.org/v2/everything"
TRUSTED_SOURCES = "bbc-news,reuters,associated-press,cnn,al-jazeera-english,the-washington-post,google-news,the-verge,techcrunch,wired,bloomberg,business-insider,espn,bbc-sport,usa-today,time,independent,nbc-news,fox-news"

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub("[أإآ]", "ا", text)
    text = text.replace("ة", "ه").replace("ى", "ي")
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()

def get_embeddings(texts, tokenizer, model, device):
    model.eval()
    all_vecs = []
    batch_size = 4
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        inputs = tokenizer(
            batch, padding=True, truncation=True,
            return_tensors="pt", max_length=128
        ).to(device)
        with torch.no_grad():
            outputs = model(**inputs)
        all_vecs.append(outputs.last_hidden_state[:, 0, :].cpu().numpy())
    return np.vstack(all_vecs)

class FakeNewsAgentModel:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-multilingual-uncased")
        self.bert = AutoModel.from_pretrained("bert-base-multilingual-uncased").to(self.device)
        self.clf = LogisticRegression(max_iter=1000)
        print(f"✅ BERT Loaded on {self.device}")

    def train(self, texts, labels):
        X = get_embeddings(texts, self.tokenizer, self.bert, self.device)
        y = np.array([1 if l == "fake" else 0 for l in labels])
        self.clf.fit(X, y)

    def predict_proba(self, text):
        X = get_embeddings([text], self.tokenizer, self.bert, self.device)
        return float(self.clf.predict_proba(X)[0][1])

def verify_with_newsapi(query: str) -> List[Tuple[str, float, str]]:
    if not NEWS_API_KEY or NEWS_API_KEY == "YOUR_API_KEY_HERE":
        return []

    search_query = query[:100]
    params = {
        "q": search_query,
        "sources": TRUSTED_SOURCES,
        "sortBy": "relevancy",
        "pageSize": 5,
        "apiKey": NEWS_API_KEY
    }
    
    found_articles = []
    try:
        r = requests.get(NEWS_ENDPOINT, params=params, timeout=5)
        data = r.json()
        articles = data.get("articles", [])
        if articles:
            titles = [a["title"] for a in articles]
            tfidf = TfidfVectorizer().fit_transform([query] + titles)
            cosine_sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()

            for i, score in enumerate(cosine_sims):
                if score > 0.1: 
                    found_articles.append((articles[i]["title"], float(score), "NewsAPI (Official)"))
    except Exception as e:
        print(f"NewsAPI Error: {e}")

    return found_articles

def verify_with_google(query: str) -> List[Tuple[str, float, str]]:
    print("🌍 Searching Google News...")
    found_articles = []
    
    is_arabic = bool(re.search('[\u0600-\u06FF]', query))
    
    if is_arabic:
        lang = 'ar'
        country = 'SA'
    else:
        lang = 'en'
        country = 'US'

    try:
        google_news = GNews(language=lang, country=country, period='7d', max_results=5)
        results = google_news.get_news(query[:100])
        
        if results:
            titles = [res.get('title', '') for res in results]
            if titles:
                tfidf = TfidfVectorizer().fit_transform([query] + titles)
                cosine_sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
                threshold = 0.05 if is_arabic else 0.1
                for i, score in enumerate(cosine_sims):
                    if score > threshold:
                        found_articles.append((results[i]['title'], float(score), "Google News"))
    except Exception as e:
        print(f"Google News Error: {e}")
        
    return found_articles

def analyze_news(agent, text, source=""):
    p_fake_bert = agent.predict_proba(text)
    
    evidence = verify_with_newsapi(text)
    if not evidence:
        evidence = verify_with_google(text)
    
    if evidence and len(evidence) > 0:
        final_p_fake = p_fake_bert - 0.8
    else:
        if p_fake_bert > 0.60:
            final_p_fake = p_fake_bert
        else:
            final_p_fake = 0.50 

    final_p_fake = max(0.0, min(1.0, final_p_fake))

    if final_p_fake > 0.60:
        label = "fake"
    elif final_p_fake < 0.30:
        label = "real"
    else:
        label = "suspicious"

    return {
        "label": label,
        "p_fake": float(final_p_fake),
        "final_score": float(1 - final_p_fake) if label == "real" else float(final_p_fake),
        "source_score": 0.95 if evidence else 0.1,
        "evidence": evidence,
        "top_terms": [("DeepLearning_Analysis", round(p_fake_bert, 2))],
        "source_type": "Hybrid (BERT + Google/NewsAPI)"
    }

def train_and_evaluate():
    X_train = [
        "Apple announces new iPhone with advanced features",
        "Saudi Arabia launches green initiative",
        "Oil prices drop significantly due to market changes",
        "Shocking: Eating dirt cures all diseases instantly",
        "Aliens confirmed to be living in New York sewers",
        "Government admits earth is flat in leaked documents",
        "Breaking: Water found on Mars by NASA",
        "Scientists confirm climate change is accelerating",
        "Free money given away by billionaire today click here",
        "Secret magical pill makes you fly instantly"
    ]
    y_train = ["real", "real", "real", "fake", "fake", "fake", "real", "real", "fake", "fake"]

    agent = FakeNewsAgentModel()
    agent.train(X_train, y_train)

    return agent