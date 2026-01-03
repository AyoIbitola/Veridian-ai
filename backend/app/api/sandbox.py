from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.engines.sandbox import sandbox

router = APIRouter()

@router.post("/process")
async def process_file(
    file: UploadFile = File(...),
    instruction: str = Form("extract_summary")
):
    """
    Uploads a file to the Secure Sandbox.
    The Sandbox extracts data based on the instruction while stripping potential malicious commands.
    """
    if not file:
         raise HTTPException(status_code=400, detail="No file uploaded")
         
    try:
        content = await file.read()
        result = sandbox.process_file_content(file.filename, content, instruction)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
