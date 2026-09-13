"""
Video processing module for extracting frames and ROI regions from ACC gameplay videos.
"""

import cv2
import numpy as np
from typing import Generator, Dict, Tuple


class VideoProcessor:
    """Handles video loading and frame extraction."""
    
    def __init__(self, video_path: str, roi_config: Dict):
        """
        Initialize video processor.
        
        Args:
            video_path: Path to the input video file
            roi_config: Dictionary containing ROI coordinates for throttle, brake, steering
        """
        self.video_path = video_path
        self.roi_config = roi_config
        self.cap = None
        self.fps = None
        self.frame_count = None
        self.current_frame = None  # Store current frame for lap detector access
        
    def open_video(self) -> bool:
        """
        Open the video file and extract metadata.
        
        Returns:
            True if video opened successfully, False otherwise
        """
        self.cap = cv2.VideoCapture(self.video_path)
        
        if not self.cap.isOpened():
            return False
            
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        return True
    
    def extract_roi(self, frame: np.ndarray, roi_name: str) -> np.ndarray:
        """
        Extract a specific ROI from a frame.
        
        Args:
            frame: Full video frame
            roi_name: Name of ROI (throttle, brake, steering)
            
        Returns:
            Cropped ROI region
        """
        roi = self.roi_config[roi_name]
        x, y, w, h = roi['x'], roi['y'], roi['width'], roi['height']
        return frame[y:y+h, x:x+w]

    def frame_rois(self, frame: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Crop the HUD regions this profile defines.

        Throttle and brake are required. Steering and the track map are
        omitted when the profile does not include them. Assetto Corsa
        original has neither on screen.

        Args:
            frame: Full video frame

        Returns:
            Mapping of ROI name to cropped image
        """
        roi_dict = {
            'throttle': self.extract_roi(frame, 'throttle'),
            'brake': self.extract_roi(frame, 'brake'),
        }
        if 'steering' in self.roi_config:
            roi_dict['steering'] = self.extract_roi(frame, 'steering')
        if 'track_map' in self.roi_config:
            roi_dict['track_map'] = self.extract_roi(frame, 'track_map')
        return roi_dict
    
    def process_frames(self) -> Generator[Tuple[int, float, Dict[str, np.ndarray]], None, None]:
        """
        Generator that yields frame data with ROI regions.
        
        Yields:
            Tuple of (frame_number, timestamp, roi_dict)
            where roi_dict contains cropped images for the ROIs in this profile
            (throttle and brake always; steering and track_map when configured)
        """
        if self.cap is None:
            raise RuntimeError("Video not opened. Call open_video() first.")
        
        frame_num = 0
        
        while True:
            ret, frame = self.cap.read()
            
            if not ret:
                break
            
            # Store current frame for lap detector access
            self.current_frame = frame
            
            timestamp = frame_num / self.fps
            
            roi_dict = self.frame_rois(frame)
            
            yield frame_num, timestamp, roi_dict
            frame_num += 1
    
    def close(self):
        """Release video capture resources."""
        if self.cap is not None:
            self.cap.release()
    
    def get_video_info(self) -> Dict:
        """
        Get video metadata.
        
        Returns:
            Dictionary with fps, frame_count, duration
        """
        return {
            'fps': self.fps,
            'frame_count': self.frame_count,
            'duration': self.frame_count / self.fps if self.fps else 0,
            'width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if self.cap else 0,
            'height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if self.cap else 0
        }

