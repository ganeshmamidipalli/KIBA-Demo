from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
from simple_web_search import run_web_search

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/vendor_finder")
async def vendor_finder(req: Request):
    body = await req.json()
    selected_variant = body.get("selected_variant", {})
    generated_query = body.get("generated_query", "")
    if not generated_query:
        title = selected_variant.get("title", "")
        generated_query = f"i want the best {title} with links with 10 vendors"

    output_text = run_web_search(generated_query)

    return JSONResponse({
        "query": generated_query,
        "output_text": output_text,
        "results": []
    })


