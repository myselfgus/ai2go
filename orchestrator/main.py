import os
from typing import Any, Dict

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse


app = FastAPI(title="gopilot-orchestrator", version="0.1.0")


def _get_upstream_config() -> tuple[str, Dict[str, str]]:
    # Preferir Prediction API se configurado
    predict_url = os.getenv("UPSTREAM_PREDICT_URL", "").rstrip("/")
    completions_url = os.getenv("UPSTREAM_CHAT_COMPLETIONS_URL", "").rstrip("/")
    base_url = os.getenv("UPSTREAM_API_BASE_URL", "").rstrip("/")

    if predict_url:
        upstream_url = predict_url
    elif completions_url:
        upstream_url = completions_url
    elif base_url:
        upstream_url = f"{base_url}/v1/chat/completions"
    else:
        raise RuntimeError("Configure UPSTREAM_PREDICT_URL ou UPSTREAM_CHAT_COMPLETIONS_URL")

    if "localhost" in upstream_url or "127.0.0.1" in upstream_url:
        raise RuntimeError("PROIBIDO LOCALHOST em upstream")

    auth_mode = os.getenv("UPSTREAM_AUTH", "bearer").lower()
    headers: Dict[str, str] = {"Content-Type": "application/json"}

    if auth_mode == "bearer":
        api_key = os.getenv("UPSTREAM_API_KEY", "")
        if not api_key:
            raise RuntimeError("UPSTREAM_API_KEY é obrigatório para UPSTREAM_AUTH=bearer")
        headers["Authorization"] = f"Bearer {api_key}"
    elif auth_mode == "gcloud":
        token = os.getenv("GOOGLE_ACCESS_TOKEN", "")
        if not token:
            raise RuntimeError(
                "GOOGLE_ACCESS_TOKEN é obrigatório para UPSTREAM_AUTH=gcloud"
            )
        headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "none":
        pass
    else:
        raise RuntimeError(f"UPSTREAM_AUTH inválido: {auth_mode}")

    return upstream_url, headers


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/v1/models")
async def list_models():
    default_model = os.getenv("UPSTREAM_DEFAULT_MODEL", "openai/gpt-oss-120b-maas")
    return {
        "object": "list",
        "data": [
            {"id": default_model, "object": "model"},
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        base_url, headers = _get_upstream_config()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    body: Dict[str, Any] = await request.json()
    if not body.get("model"):
        body["model"] = os.getenv("UPSTREAM_DEFAULT_MODEL", "openai/gpt-oss-120b-maas")

    # Pass-through para endpoint OpenAI-compatível (URL completa) ou Prediction API
    upstream_url = base_url
    try:
        predict_url = os.getenv("UPSTREAM_PREDICT_URL", "").rstrip("/")
        if predict_url:
            instance: Dict[str, Any] = {
                "@requestFormat": "chatCompletions",
                "messages": body.get("messages", []),
            }
            if "max_tokens" in body:
                instance["max_tokens"] = body["max_tokens"]
            if "temperature" in body:
                instance["temperature"] = body["temperature"]
            payload = {"instances": [instance]}

            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(predict_url, json=payload, headers=headers)
            if resp.status_code >= 400:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)

            vertex = resp.json()
            # Try to map Vertex predictions -> OpenAI chat.completion
            pred = vertex.get("predictions") or {}
            # predictions may be a list or object; normalize
            if isinstance(pred, list) and pred:
                pred = pred[0]
            choices = pred.get("choices") or []
            created = pred.get("created")
            oid = pred.get("id")
            model = pred.get("model") or body.get("model")
            usage = pred.get("usage") or {}

            # If streaming requested, simulate SSE with delta chunks
            if bool(body.get("stream")) and choices:
                content = choices[0].get("message", {}).get("content", "")

                async def sse_iter():
                    # send role first
                    first_event = {
                        "id": oid or "chatcmpl",
                        "object": "chat.completion.chunk",
                        "model": model,
                        "choices": [
                            {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}
                        ],
                    }
                    yield f"data: {first_event}\n\n"
                    # chunk content
                    chunk_size = max(20, len(content) // 20 or 1)
                    for i in range(0, len(content), chunk_size):
                        piece = content[i : i + chunk_size]
                        event = {
                            "id": oid or "chatcmpl",
                            "object": "chat.completion.chunk",
                            "model": model,
                            "choices": [
                                {"index": 0, "delta": {"content": piece}, "finish_reason": None}
                            ],
                        }
                        yield f"data: {event}\n\n"
                    # done event
                    done_event = {
                        "id": oid or "chatcmpl",
                        "object": "chat.completion.chunk",
                        "model": model,
                        "choices": [
                            {"index": 0, "delta": {}, "finish_reason": choices[0].get("finish_reason") or "stop"}
                        ],
                    }
                    yield f"data: {done_event}\n\n"
                    yield "data: [DONE]\n\n"

                return StreamingResponse(sse_iter(), media_type="text/event-stream")

            # Non-stream response in OpenAI format
            openai = {
                "id": oid or "chatcmpl",
                "object": "chat.completion",
                "created": created,
                "model": model,
                "choices": choices,
                "usage": usage,
            }
            return JSONResponse(status_code=200, content=openai)
        else:
            if bool(body.get("stream")):
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("POST", upstream_url, json=body, headers=headers) as resp:
                        if resp.status_code >= 400:
                            text = await resp.aread()
                            raise HTTPException(status_code=resp.status_code, detail=text.decode("utf-8", errors="ignore"))

                        async def iter_bytes():
                            async for chunk in resp.aiter_bytes():
                                yield chunk

                        media_type = resp.headers.get("content-type", "application/json")
                        return StreamingResponse(iter_bytes(), status_code=resp.status_code, media_type=media_type)
            else:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(upstream_url, json=body, headers=headers)
                if resp.status_code >= 400:
                    raise HTTPException(status_code=resp.status_code, detail=resp.text)
                return JSONResponse(status_code=resp.status_code, content=resp.json())
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Erro ao conectar ao upstream: {e}")


@app.post("/vertex/predict")
async def vertex_predict_passthrough(request: Request):
    predict_url = os.getenv("UPSTREAM_PREDICT_URL", "").rstrip("/")
    if not predict_url:
        raise HTTPException(status_code=503, detail="Defina UPSTREAM_PREDICT_URL")
    if "localhost" in predict_url or "127.0.0.1" in predict_url:
        raise HTTPException(status_code=400, detail="PROIBIDO LOCALHOST em UPSTREAM_PREDICT_URL")

    auth_mode = os.getenv("UPSTREAM_AUTH", "gcloud").lower()
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if auth_mode == "gcloud":
        token = os.getenv("GOOGLE_ACCESS_TOKEN", "")
        if not token:
            raise HTTPException(status_code=503, detail="GOOGLE_ACCESS_TOKEN é obrigatório para UPSTREAM_AUTH=gcloud")
        headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "bearer":
        key = os.getenv("UPSTREAM_API_KEY", "")
        if not key:
            raise HTTPException(status_code=503, detail="UPSTREAM_API_KEY é obrigatório para UPSTREAM_AUTH=bearer")
        headers["Authorization"] = f"Bearer {key}"

    payload = await request.json()
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(predict_url, json=payload, headers=headers)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return JSONResponse(status_code=resp.status_code, content=resp.json())
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Erro ao conectar ao Vertex: {e}")


@app.post("/tools/{name}/invoke")
async def toolbox_invoke(name: str, request: Request):
    base = os.getenv("GENAI_TOOLBOX_URL", "").rstrip("/")
    if not base:
        raise HTTPException(status_code=503, detail="Defina GENAI_TOOLBOX_URL")
    if "localhost" in base or "127.0.0.1" in base:
        raise HTTPException(status_code=400, detail="PROIBIDO LOCALHOST em GENAI_TOOLBOX_URL")

    payload = await request.body()
    url = f"{base}/api/tool/{name}/invoke"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, content=payload, headers={"Content-Type": "application/json"})
    return JSONResponse(status_code=resp.status_code, content=resp.json() if resp.content else {})
