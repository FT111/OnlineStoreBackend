from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any


router = APIRouter(prefix="/listings", tags=["listings"])

router.get("/", response_model=List[Dict[str, Any]])