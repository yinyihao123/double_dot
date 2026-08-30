from fastapi import FastAPI
from agent import run_agent


app = FastAPI()


@app.get("/")
def home():
    return {
        "message": "My Agent is running"
    }


@app.get("/chat")
def chat(question: str):

    answer = run_agent(question)

    return {
        "question": question,
        "answer": answer
    }