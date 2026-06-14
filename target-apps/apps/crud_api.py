from itertools import count

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="pLoadtesting Target Suite - CRUD API",
    version="1.0.0",
    description="Low-cost in-memory CRUD workload suitable for local and CI smoke tests.",
)

_items: dict[int, dict] = {}
_counter = count(1)


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    value: int = Field(default=0, ge=0, le=1_000_000)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "target_app_id": "crud-api"}


@app.get("/api/items")
async def list_items() -> dict:
    return {"items": list(_items.values()), "count": len(_items)}


@app.post("/api/items", status_code=201)
async def create_item(body: ItemCreate) -> dict:
    item_id = next(_counter)
    item = {"id": item_id, "name": body.name, "value": body.value}
    _items[item_id] = item
    return item


@app.get("/api/items/{item_id}")
async def get_item(item_id: int) -> dict:
    item = _items.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found.")
    return item

