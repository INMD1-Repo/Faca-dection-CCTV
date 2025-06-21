from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from services.face_learning_service import learn_new_face_from_video

router = APIRouter(prefix="/faces", tags=["Face Learning"])

@router.post("/learn_video")
async def learn_face_video(
    person_name: str = Form(...),
    video_file: UploadFile = File(...)
):
    try:
        video_bytes = await video_file.read()
        if not video_bytes:
            raise HTTPException(status_code=400, detail="빈 영상 파일입니다.")

        result = await learn_new_face_from_video(person_name, video_bytes)
        return JSONResponse(content=result)

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"서버 처리 오류: {str(e)}")
