"""Video processing service for telemetry extraction."""

import yaml
import time
import cv2
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd

from ...video_processor import VideoProcessor
from ...telemetry_extractor import TelemetryExtractor
from ...lap_detector import LapDetector
from ...position_tracker_v2 import PositionTrackerV2
from ...interactive_visualizer import InteractiveTelemetryVisualizer

from ..config import settings
from ..models import VideoMetadata, LapMetadata
from .storage import StorageService


class VideoProcessingService:
    """Handles video processing and telemetry extraction."""

    def __init__(self):
        self.storage = StorageService()
        self.config_path = settings.roi_config_path

    def load_roi_config(self) -> dict:
        """Load ROI configuration from YAML file."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    @staticmethod
    def list_roi_profiles(full_config: dict) -> Dict[str, dict]:
        """Return named ROI profiles from the YAML config.

        Supports both the current multi-profile format (top-level keys like
        ``twitch_720p``) and the older flat format (``throttle`` at the root).
        """
        if not full_config:
            return {}

        if 'throttle' in full_config:
            return {'default': full_config}

        return {
            name: cfg
            for name, cfg in full_config.items()
            if isinstance(cfg, dict) and 'throttle' in cfg
        }

    def select_roi_profile(
        self,
        full_config: dict,
        video_height: int,
        has_overlay: bool = False,
        profile_name: Optional[str] = None
    ) -> Tuple[str, dict]:
        """Choose an ROI profile from YAML using an explicit name or video height.

        Profile names are expected to include a resolution suffix such as
        ``720p`` or ``1080p`` (e.g. ``my_ps5_1080p``). When several profiles
        match the same height, ``has_overlay`` prefers overlay-oriented names
        (``go_setups`` / ``overlay``).

        Returns:
            Tuple of (profile_name, roi_config dict).

        Raises:
            ValueError: If no matching profile is found.
        """
        profiles = self.list_roi_profiles(full_config)
        if not profiles:
            raise ValueError("No ROI profiles found in roi_config.yaml")

        if profile_name:
            if profile_name not in profiles:
                available = ", ".join(profiles)
                raise ValueError(
                    f"Unknown ROI profile '{profile_name}'. Available: {available}"
                )
            return profile_name, profiles[profile_name]

        height_tag = f"{video_height}p"
        matching = [name for name in profiles if height_tag in name]

        if not matching:
            available = ", ".join(profiles)
            raise ValueError(
                f"No ROI profile for {video_height}p video. "
                f"Available profiles: {available}"
            )

        if has_overlay:
            overlay_matches = [
                name for name in matching
                if 'go_setups' in name or 'overlay' in name
            ]
            if overlay_matches:
                chosen = overlay_matches[0]
                return chosen, profiles[chosen]

        default_matches = [
            name for name in matching
            if 'go_setups' not in name and 'overlay' not in name
        ]
        chosen = (default_matches or matching)[0]
        return chosen, profiles[chosen]

    async def process_video(
        self,
        video_path: str,
        video_name: str,
        has_overlay: bool = False,
        profile_name: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> VideoMetadata:
        """
        Process a video and extract telemetry data.

        Args:
            video_path: Path to the video file
            video_name: Sanitized name for output directory
            has_overlay: Prefer overlay-oriented 720p profiles (e.g. Go Setups)
            profile_name: Explicit ROI profile name; otherwise chosen from video height
            progress_callback: Optional callback for progress updates (percentage, message)

        Returns:
            VideoMetadata object

        Raises:
            FileNotFoundError: If video file doesn't exist
            ValueError: If video cannot be opened
        """
        video_path_obj = Path(video_path)

        if not video_path_obj.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Load configuration and pick a profile that matches this video
        full_config = self.load_roi_config()

        probe = cv2.VideoCapture(video_path)
        if not probe.isOpened():
            raise ValueError("Could not open video file")
        video_height = int(probe.get(cv2.CAP_PROP_FRAME_HEIGHT))
        probe.release()

        selected_profile, roi_config = self.select_roi_profile(
            full_config,
            video_height=video_height,
            has_overlay=has_overlay,
            profile_name=profile_name
        )

        if progress_callback:
            progress_callback(
                2,
                f"Using ROI profile '{selected_profile}' for {video_height}p video"
            )

        # Initialize components
        processor = VideoProcessor(video_path, roi_config)
        extractor = TelemetryExtractor()

        lap_roi_config = roi_config.copy()
        if 'lap_number_training' in roi_config:
            lap_roi_config['lap_number'] = roi_config['lap_number_training']

        lap_detector = LapDetector(lap_roi_config, enable_performance_stats=False)
        position_tracker = PositionTrackerV2()

        if not processor.open_video():
            raise ValueError("Could not open video file")

        try:
            # Get video info
            video_info = processor.get_video_info()

            if progress_callback:
                progress_callback(5, "Video opened successfully")

            # Extract track path if available
            if 'track_map' in roi_config:
                if progress_callback:
                    progress_callback(10, "Extracting track path from minimap...")

                sample_frames = [0, 50, 100, 150, 200, 250, 500, 750, 1000, 1250, 1500]
                map_rois = []

                for sample_frame_num in sample_frames:
                    if sample_frame_num >= video_info['frame_count']:
                        break

                    processor.cap.set(cv2.CAP_PROP_POS_FRAMES, sample_frame_num)
                    ret, frame = processor.cap.read()

                    if ret:
                        map_roi = processor.extract_roi(frame, 'track_map')
                        map_rois.append(map_roi)

                processor.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

                if position_tracker.extract_track_path(map_rois):
                    if progress_callback:
                        progress_callback(15, "Track path extraction successful")
                else:
                    if progress_callback:
                        progress_callback(15, "Warning: Track path extraction failed")

            # Process frames
            if progress_callback:
                progress_callback(20, "Processing frames and extracting telemetry...")
            
            total_frames = video_info['frame_count']
            print(f"Starting frame processing loop for {total_frames} frames...")

            telemetry_data = []
            previous_lap = None
            lap_transitions = []
            completed_lap_times = {}
            frames_since_transition = 0

            last_progress_pct = 20

            print(f"Starting frame processing loop for {total_frames} frames...")

            for frame_num, timestamp, roi_dict in processor.process_frames():
                # Extract telemetry
                telemetry = extractor.extract_frame_telemetry(roi_dict)

                # Extract lap number, speed, gear
                lap_number = lap_detector.extract_lap_number(processor.current_frame)
                speed = lap_detector.extract_speed(processor.current_frame)
                gear = lap_detector.extract_gear(processor.current_frame)

                # Extract track position
                track_position = None
                if 'track_map' in roi_dict and position_tracker.is_ready():
                    track_position = position_tracker.extract_position(roi_dict['track_map'])

                # Detect lap transitions
                if lap_detector.detect_lap_transition(lap_number, previous_lap):
                    frames_since_transition = 1
                    position_tracker.reset_for_new_lap()

                    if 'track_map' in roi_dict and position_tracker.is_ready():
                        track_position = position_tracker.extract_position(roi_dict['track_map'])

                    lap_transitions.append({
                        'frame': frame_num,
                        'time': timestamp,
                        'from_lap': previous_lap,
                        'to_lap': lap_number,
                        'completed_lap_time': None
                    })
                elif frames_since_transition == 1:
                    completed_lap_time = lap_detector.extract_last_lap_time(processor.current_frame)

                    if completed_lap_time and previous_lap is not None:
                        completed_lap_times[previous_lap] = completed_lap_time

                        if lap_transitions:
                            lap_transitions[-1]['completed_lap_time'] = completed_lap_time

                    frames_since_transition = 0

                # Store data
                telemetry_data.append({
                    'frame': frame_num,
                    'time': timestamp,
                    'lap_number': lap_number,
                    'lap_time': None,
                    'track_position': track_position,
                    'speed': speed,
                    'gear': gear,
                    'throttle': telemetry['throttle'],
                    'brake': telemetry['brake'],
                    'steering': telemetry['steering'],
                    'tc_active': telemetry['tc_active'],
                    'abs_active': telemetry['abs_active']
                })

                previous_lap = lap_number

                # Progress update (every 5%)
                current_progress_pct = 20 + int((frame_num / total_frames) * 60)
                if current_progress_pct > last_progress_pct and current_progress_pct % 5 == 0:
                    if progress_callback:
                        progress_callback(current_progress_pct, f"Processing frames: {frame_num}/{total_frames} ({int(frame_num/total_frames*100)}%)")
                    last_progress_pct = current_progress_pct

            # Finalize lap detection
            final_lap = lap_detector.finalize_lap_detection()
            if final_lap is not None and (previous_lap is None or final_lap > previous_lap):
                if previous_lap is not None and final_lap == previous_lap + 1:
                    for entry in reversed(telemetry_data):
                        if entry['lap_number'] == previous_lap:
                            entry['lap_number'] = final_lap
                        else:
                            break

            # Add lap times to telemetry data
            for entry in telemetry_data:
                lap_num = entry['lap_number']
                entry['lap_time'] = completed_lap_times.get(lap_num, None)

            if progress_callback:
                progress_callback(85, "Generating outputs...")

            # Create DataFrame
            visualizer = InteractiveTelemetryVisualizer(
                output_dir=str(self.storage.get_video_directory(video_name))
            )
            df = visualizer.create_dataframe(telemetry_data)

            # Save CSV
            csv_filename = "telemetry.csv"
            csv_path = visualizer.export_csv(df, filename=csv_filename)

            if progress_callback:
                progress_callback(90, "Generating metadata...")

            # Generate metadata
            summary = visualizer.generate_summary(df)
            metadata = self._create_metadata(
                video_name=video_name,
                video_path=video_path,
                video_info=video_info,
                summary=summary,
                csv_path=csv_path
            )

            # Save metadata
            self.storage.save_metadata(video_name, metadata)

            if progress_callback:
                progress_callback(100, "Processing complete!")

            return metadata

        finally:
            processor.close()

    def _create_metadata(
        self,
        video_name: str,
        video_path: str,
        video_info: Dict,
        summary: Dict,
        csv_path: str
    ) -> VideoMetadata:
        """
        Create VideoMetadata object from processing results.

        Args:
            video_name: Sanitized video name
            video_path: Original video path
            video_info: Video information dict
            summary: Summary statistics dict
            csv_path: Path to CSV file

        Returns:
            VideoMetadata object
        """
        # Create lap metadata
        laps = []
        for lap_info in summary.get('laps', []):
            laps.append(LapMetadata(
                lap_number=lap_info['lap_number'],
                duration=lap_info['duration'],
                frames=lap_info['frames'],
                avg_speed=lap_info.get('avg_speed'),
                max_speed=lap_info.get('max_speed'),
                avg_throttle=lap_info.get('avg_throttle'),
                avg_brake=lap_info.get('avg_brake'),
                lap_time=None  # Will be filled if available
            ))

        return VideoMetadata(
            video_name=video_name,
            video_path=video_path,
            fps=video_info['fps'],
            duration=video_info['duration'],
            frame_count=video_info['frame_count'],
            total_laps=summary.get('total_laps', 0),
            laps=laps,
            processed_at=datetime.now().isoformat(),
            csv_path=csv_path,
            track_position_available=summary.get('track_position_tracked', False)
        )
