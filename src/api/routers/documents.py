"""
Sprint 6, Day 40: GET /api/v1/companies/{ticker}/documents
"""

from fastapi import APIRouter, Depends, HTTPException

from src.api.database import get_db_connection

router = APIRouter()


@router.get("/companies/{ticker}/documents")
def get_company_documents(ticker: str, conn=Depends(get_db_connection)):
    """Get company documents for the given ticker, conn."""
    if conn.execute("SELECT 1 FROM companies WHERE id = ?", (ticker,)).fetchone() is None:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    rows = conn.execute(
        'SELECT "Year" AS year, "Annual_Report" AS annual_report FROM documents WHERE company_id = ? ORDER BY "Year" DESC',
        (ticker,),
    ).fetchall()

    documents = []
    for row in rows:
        url = row["annual_report"]
        is_url_valid = isinstance(url, str) and url.startswith("http")
        documents.append({"year": row["year"], "annual_report": url, "is_url_valid": is_url_valid})

    return {"company_id": ticker, "count": len(documents), "documents": documents}
