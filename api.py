import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel
import httpx
import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from preproc import TextPreProcessor

MODEL_DIR = "./bert_sentiment_model"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class SentimentClassifier(nn.Module):
    def __init__(self, pretrained_model_name="distilbert-base-uncased", num_labels=2):
        super(SentimentClassifier, self).__init__()
        self.model = AutoModel.from_pretrained(pretrained_model_name)
        self.dropout = nn.Dropout(p=0.3)
        self.classifier = nn.Linear(self.model.config.hidden_size, num_labels)

    def forward(self, input_ids, attention_mask):
        outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
        last_hidden_state = outputs.last_hidden_state
        pooled_output = last_hidden_state[:, 0]
        dropped = self.dropout(pooled_output)
        logits = self.classifier(dropped)
        return logits


if not os.path.exists(MODEL_DIR):
    raise RuntimeError(
        f"Model directory not found at {MODEL_DIR}. Please download and unzip it."
    )

with open(os.path.join(MODEL_DIR, "class_mappings.json"), "r") as f:
    idx_to_class = {int(k): v for k, v in json.load(f).items()}
num_labels = len(idx_to_class)

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)

model = SentimentClassifier(
    pretrained_model_name="distilbert-base-uncased", num_labels=num_labels
)

model.load_state_dict(
    torch.load(os.path.join(MODEL_DIR, "pytorch_model.bin"), map_location=DEVICE)
)
model.to(DEVICE)
model.eval()

preprocessor = TextPreProcessor()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://0.0.0.0:8080", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
X_API_BASE_URL = "https://api.x.com/2"


@app.get("/api/tweets/{username}")
async def get_tweets_middlewr(username: str):
    if not X_BEARER_TOKEN:
        raise HTTPException(
            status_code=500, detail="X API Bearer Token is not configured."
        )
    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
    async with httpx.AsyncClient() as client:
        try:
            user_url = f"{X_API_BASE_URL}/users/by/username/{username}"
            user_resp = await client.get(user_url, headers=headers)
            user_resp.raise_for_status()
            user_id = user_resp.json()["data"]["id"]
            tweets_url = f"{X_API_BASE_URL}/users/{user_id}/tweets"
            tweets_resp = await client.get(
                tweets_url, params={"max_results": 10}, headers=headers
            )
            tweets_resp.raise_for_status()
            return tweets_resp.json().get("data", [])
        except httpx.HTTPStatusError as e:
            return JSONResponse(
                status_code=e.response.status_code,
                content={"detail": f"Error from X API: {e.response.text}"},
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"An internal error occurred: {str(e)}"
            )


class ClassificationRequest(BaseModel):
    text: str


@app.post("/classification/")
def return_classification(request: ClassificationRequest) -> JSONResponse:
    proc_text = preprocessor.preprocess(request.text)
    inputs = tokenizer(
        proc_text, return_tensors="pt", truncation=True, padding=True, max_length=96
    ).to(DEVICE)

    with torch.no_grad():
        logits = model(
            input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"]
        )

    scores = torch.softmax(logits, dim=1).squeeze().cpu().numpy()
    predicted_idx = torch.argmax(logits, dim=1).item()
    predicted_class = idx_to_class.get(predicted_idx, "Unknown")

    if scores.shape == ():
        decision_scores = {idx_to_class[i]: float(scores) for i in range(num_labels)}
    else:
        decision_scores = {
            idx_to_class[i]: float(score) for i, score in enumerate(scores)
        }

    response = {
        "predicted_class": predicted_class,
        "decision_scores": decision_scores,
    }

    return JSONResponse(content=response)
