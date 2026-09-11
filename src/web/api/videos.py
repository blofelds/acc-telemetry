"""API endpoints for video management."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from typing import List
from pathlib import Path
import shutil
import cv2
from datetime import datetime

from ..models import VideoProcessRequest, VideoMetadata, VideoListItem
from ..services.storage import StorageService
from ..services.processing import VideoProcessingService
from ..services.jobs import job_manager

router = APIRouter()
storage = StorageService()
processing = VideoProcessingService()


@router.post("/upload", response_model=VideoMetadata)
async def upload_video(
    file: UploadFile = File(...),
    has_overlay: bool = Form(False),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Upload a video file and start processing it.

    Args:
        file: The video file to upload
        background_tasks: FastAPI background tasks

    Returns:
        VideoMetadata object (initially with processing status)
    """
    # Validate file type
    if not file.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="File must be a video")
    
    # Save file to input directory
    video_name = storage.sanitize_filename(file.filename)
    file_path = storage.get_video_path(video_name)
    
    # Ensure input directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()
            
    # Reject uploads that have no matching ROI profile for this resolution
    cap = cv2.VideoCapture(str(file_path))
    if cap.isOpened():
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        try:
            processing.select_roi_profile(
                processing.load_roi_config(),
                video_height=height,
                has_overlay=has_overlay
            )
        except ValueError as e:
            file_path.unlink()
            raise HTTPException(status_code=400, detail=str(e))
    
    # Check if already processed (if re-uploading)
    if storage.video_exists(video_name):
        # If it exists, we might want to re-process or just return existing
        # For now, let's assume re-upload means re-process, so we delete old data
        storage.delete_video(video_name)

    # Create job
    job_id = job_manager.create_job(video_name)

    # Define progress callback
    def progress_callback(progress: int, message: str):
        job_manager.update_job(
            job_id=job_id,
            status="processing",
            progress=progress,
            message=message
        )

    # Define background task
    async def process_task():
        try:
            job_manager.update_job(job_id, status="processing", progress=0, message="Starting processing...")

            await processing.process_video(
                video_path=str(file_path),
                video_name=video_name,
                has_overlay=has_overlay,
                progress_callback=progress_callback
            )

            job_manager.complete_job(job_id, message=f"Video '{video_name}' processed successfully")

        except Exception as e:
            job_manager.fail_job(job_id, error=str(e))

    # Add to background tasks
    background_tasks.add_task(process_task)

    # Return initial metadata (simulated since processing just started)
    return VideoMetadata(
        video_name=video_name,
        video_path=str(file_path),
        duration=0,
        fps=0,
        frame_count=0,
        total_laps=0,
        laps=[],
        processed_at=datetime.now().isoformat(),
        csv_path="",
        track_position_available=False
    )


@router.get("", response_model=List[VideoListItem])
async def list_videos():
    """
    Get a list of all processed videos.

    Returns:
        List of VideoListItem objects
    """
    videos = storage.list_videos()
    return videos


@router.get("/{video_name}", response_model=VideoMetadata)
async def get_video_metadata(video_name: str):
    """
    Get metadata for a specific video.

    Args:
        video_name: Name of the video

    Returns:
        VideoMetadata object
    """
    metadata = storage.load_metadata(video_name)

    if metadata is None:
        raise HTTPException(status_code=404, detail="Video not found")

    return metadata


@router.post("/process")
async def process_video(request: VideoProcessRequest, background_tasks: BackgroundTasks):
    """
    Start processing a video file.

    Args:
        request: VideoProcessRequest with video_path
        background_tasks: FastAPI background tasks

    Returns:
        Job ID for tracking progress
    """
    video_path = Path(request.video_path)

    # Validate video file exists
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file not found: {request.video_path}")

    # Sanitize video name
    video_name = storage.sanitize_filename(video_path.name)

    # Check if already processed
    if storage.video_exists(video_name):
        raise HTTPException(
            status_code=409,
            detail=f"Video '{video_name}' has already been processed. Delete it first to reprocess."
        )

    # Create job
    job_id = job_manager.create_job(video_name)

    # Define progress callback
    def progress_callback(progress: int, message: str):
        job_manager.update_job(
            job_id=job_id,
            status="processing",
            progress=progress,
            message=message
        )

    # Define background task
    async def process_task():
        try:
            job_manager.update_job(job_id, status="processing", progress=0, message="Starting processing...")

            metadata = await processing.process_video(
                video_path=str(video_path),
                video_name=video_name,
                progress_callback=progress_callback
            )

            job_manager.complete_job(job_id, message=f"Video '{video_name}' processed successfully")

        except Exception as e:
            job_manager.fail_job(job_id, error=str(e))

    # Add to background tasks
    background_tasks.add_task(process_task)

    return {
        "job_id": job_id,
        "video_name": video_name,
        "message": "Processing started"
    }


@router.delete("/{video_name}")
async def delete_video(video_name: str):
    """
    Delete all data for a video.

    Args:
        video_name: Name of the video

    Returns:
        Success message
    """
    if not storage.video_exists(video_name):
        raise HTTPException(status_code=404, detail="Video not found")

    success = storage.delete_video(video_name)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete video")

    return {"message": f"Video '{video_name}' deleted successfully"}
