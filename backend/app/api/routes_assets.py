from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.deps import AssetsDep, DbDep

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("")
def list_assets(db: DbDep, assets: AssetsDep) -> dict:
    return {"assets": assets.list_assets(db)}


@router.post("/upload")
async def upload_asset(
    db: DbDep,
    assets: AssetsDep,
    file: UploadFile = File(...),
) -> dict:
    return await assets.save_upload(db, file)


@router.delete("/{asset_id}")
def delete_asset(asset_id: str, db: DbDep, assets: AssetsDep) -> dict:
    try:
        assets.delete_asset(db, asset_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="asset not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "asset_id": asset_id}
