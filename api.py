from fastapi import FastAPI
from pydantic import BaseModel
from core import process_user_bot

app = FastAPI()

class ClientData(BaseModel):
    client_username: str
    weburl: str

@app.post("/create-client")
def create_client(data: ClientData):
    result = process_user_bot(data.client_username, data.weburl)
    if result:
        return {"status": "success", "data": result}
    return {"status": "error", "message": "Failed to create client"}


import os

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
