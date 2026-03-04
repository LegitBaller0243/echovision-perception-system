"""
Collision Detection Service
Implements RelativeCollisionDetector functionality from TestActivity.java
"""

import numpy as np
from typing import Dict, List, Optional
from enum import Enum


class DangerLevel(Enum):
    """Danger classification levels"""
    CRITICAL_COLLISION = "CRITICAL_COLLISION"   # Immediate collision risk (< 0.5 seconds)
    HIGH_WARNING = "HIGH_WARNING"               # Very close, impending danger
    MODERATE_WARNING = "MODERATE_WARNING"       # Close, attention needed
    LOW_WARNING = "LOW_WARNING"                 # Detected but distant
    SAFE = "SAFE"                               # Far away, no concern


class CollisionDetectorService:
    """Service for collision threat detection using relative depth analysis"""
    
    def __init__(self):
        pass
    
    def analyze_scene(self, depth_map: np.ndarray) -> Dict:
        """
        Analyze scene to understand depth context
        
        Args:
            depth_map: 2D array of normalized depth values [0,1]
            
        Returns:
            Scene analysis dictionary with percentiles and thresholds
        """
        # Collect all depth values
        all_depths = depth_map.flatten()
        all_depths = all_depths[all_depths > 0]  # Filter zeros
        
        if len(all_depths) == 0:
            return {
                'backgroundDepth': 0.5,
                'foregroundThreshold': 0.7,
                'min': 0.0,
                'max': 1.0,
                'p25': 0.25,
                'p50': 0.5,
                'p75': 0.75,
                'p90': 0.9
            }
        
        # Calculate percentiles
        sorted_depths = np.sort(all_depths)
        n = len(sorted_depths)
        
        p25 = sorted_depths[n // 4]
        p50 = sorted_depths[n // 2]  # Median
        p75 = sorted_depths[3 * n // 4]
        p90 = sorted_depths[9 * n // 10]
        
        # Background = median (most of scene)
        background_depth = p50
        
        # Foreground = anything significantly above 75th percentile
        foreground_threshold = p75 + (p90 - p75) * 0.5
        
        return {
            'backgroundDepth': float(background_depth),
            'foregroundThreshold': float(foreground_threshold),
            'min': float(np.min(sorted_depths)),
            'max': float(np.max(sorted_depths)),
            'p25': float(p25),
            'p50': float(p50),
            'p75': float(p75),
            'p90': float(p90)
        }
    
    def analyze_labeled_object(self, depth_map: np.ndarray, labeled_obj: Dict, scene: Dict) -> Dict:
        """
        Analyze a labeled object region using its provided bbox
        
        Args:
            depth_map: 2D array of normalized depth values
            labeled_obj: Dictionary with objectId, label, bbox, detectionConfidence
            scene: Scene analysis dictionary
            
        Returns:
            Analyzed object dictionary
        """
        obj = {
            'objectId': labeled_obj['objectId'],
            'label': labeled_obj['label'],
            'bbox': labeled_obj['bbox'],
        }
        
        x1, y1, x2, y2 = labeled_obj['bbox']
        
        # Sample depth values in bbox
        height, width = depth_map.shape
        # Clamp bbox to valid range
        x1_clamped = max(0, min(int(x1), width - 1))
        y1_clamped = max(0, min(int(y1), height - 1))
        x2_clamped = max(0, min(int(x2), width - 1))
        y2_clamped = max(0, min(int(y2), height - 1))
        
        # Calculate center from clamped coordinates
        obj['centerX'] = (x1_clamped + x2_clamped) / 2.0
        obj['centerY'] = (y1_clamped + y2_clamped) / 2.0
        
        depth_samples = depth_map[y1_clamped:y2_clamped+1, x1_clamped:x2_clamped+1].flatten()
        depth_samples = depth_samples[depth_samples > 0]  # Filter zeros
        
        if len(depth_samples) == 0:
            obj['maxDepth'] = 0.0
            obj['medianDepth'] = 0.0
            obj['depthVariance'] = 0.0
            obj['depthGradient'] = 0.0
            return obj
        
        # Key metrics
        obj['maxDepth'] = float(np.max(depth_samples))  # Closest point
        obj['medianDepth'] = float(np.median(depth_samples))
        
        # Depth variance (how uniform is the object?)
        mean = np.mean(depth_samples)
        variance = np.mean((depth_samples - mean) ** 2)
        obj['depthVariance'] = float(variance)
        
        # Calculate depth gradient at object center
        cx = int(obj['centerX'])
        cy = int(obj['centerY'])
        obj['depthGradient'] = self._calculate_local_gradient(depth_map, cx, cy)
        
        # Direction and angle
        obj['direction'] = self._calculate_direction(obj['centerX'], obj['centerY'], width, height)
        obj['angleDeg'] = self._calculate_angle(obj['centerX'], obj['centerY'], width, height)
        
        return obj
    
    def calculate_danger_level(self, obj: Dict, scene: Dict, depth_map: np.ndarray) -> str:
        """
        Calculate collision danger level - THE CORE ALGORITHM
        
        Args:
            obj: Analyzed object dictionary
            scene: Scene analysis dictionary
            depth_map: 2D array of depth values
            
        Returns:
            Danger level string
        """
        height, width = depth_map.shape
        
        # FACTOR 1: Absolute Closeness (relative to scene range)
        depth_range = scene['max'] - scene['min']
        if depth_range > 0:
            normalized_closeness = (obj['maxDepth'] - scene['min']) / depth_range
        else:
            normalized_closeness = 0.5
        
        if normalized_closeness > 0.95:
            closeness_score = 1.0
        elif normalized_closeness > 0.85:
            closeness_score = 0.7
        elif normalized_closeness > 0.75:
            closeness_score = 0.5
        elif normalized_closeness > 0.65:
            closeness_score = 0.3
        else:
            closeness_score = 0.1
        
        # FACTOR 2: Relative to Scene Background
        if scene['backgroundDepth'] > 0:
            relative_closeness = obj['medianDepth'] / scene['backgroundDepth']
        else:
            relative_closeness = 1.0
        
        if relative_closeness > 2.0:
            relative_score = 0.8
        elif relative_closeness > 1.5:
            relative_score = 0.5
        elif relative_closeness > 1.2:
            relative_score = 0.3
        else:
            relative_score = 0.1
        
        # FACTOR 3: Position in Frame (center = more dangerous)
        center_x = width / 2.0
        center_y = height / 2.0
        dist_from_center = np.sqrt(
            (obj['centerX'] - center_x) ** 2 + 
            (obj['centerY'] - center_y) ** 2
        )
        max_dist_from_center = np.sqrt(center_x ** 2 + center_y ** 2)
        position_score = 1.0 - (dist_from_center / max_dist_from_center) if max_dist_from_center > 0 else 0.5
        
        # Boost for bottom-center (walking path)
        in_walking_path = (obj['centerY'] > height * 0.5 and 
                          abs(obj['centerX'] - center_x) < width * 0.3)
        if in_walking_path:
            position_score *= 1.3
            position_score = min(1.0, position_score)
        
        # FACTOR 4: Depth Gradient (strong edge = obstacle)
        gradient_score = min(1.0, obj['depthGradient'] * 3.0)
        
        # FACTOR 5: Object Size (larger objects more concerning)
        area = (obj['bbox'][2] - obj['bbox'][0]) * (obj['bbox'][3] - obj['bbox'][1])
        frame_area = width * height
        size_ratio = area / frame_area if frame_area > 0 else 0
        size_score = min(1.0, size_ratio * 5.0)  # Objects >20% of frame get max score
        
        # FACTOR 6: Depth Uniformity (uniform = solid object, varied = noisy/far)
        if obj['depthVariance'] < 0.01:
            uniformity_score = 1.0
        elif obj['depthVariance'] < 0.05:
            uniformity_score = 0.7
        else:
            uniformity_score = 0.3
        
        # CALCULATE TOTAL DANGER SCORE (weighted combination)
        danger_score = (
            closeness_score * 0.35 +      # Most important: how close?
            relative_score * 0.25 +       # Is it foreground or background?
            position_score * 0.20 +       # Is it in my path?
            gradient_score * 0.10 +       # Is it a real obstacle?
            size_score * 0.05 +            # How big is it?
            uniformity_score * 0.05       # Is it solid?
        )
        
        # Build explanation
        reason = (f"Closeness:{closeness_score:.2f} "
                 f"Relative:{relative_score:.2f} "
                 f"Position:{position_score:.2f} "
                 f"Total:{danger_score:.2f}")
        
        # CLASSIFY DANGER LEVEL
        if danger_score >= 0.75:
            danger_level = DangerLevel.CRITICAL_COLLISION
        elif danger_score >= 0.55:
            danger_level = DangerLevel.HIGH_WARNING
        elif danger_score >= 0.35:
            danger_level = DangerLevel.MODERATE_WARNING
        elif danger_score >= 0.20:
            danger_level = DangerLevel.LOW_WARNING
        else:
            danger_level = DangerLevel.SAFE
        
        return {
            'dangerLevel': danger_level.value,
            'confidenceScore': float(danger_score),
            'reasonForDanger': reason
        }
    
    def _calculate_local_gradient(self, depth_map: np.ndarray, x: int, y: int) -> float:
        """Calculate local depth gradient (edge strength)"""
        height, width = depth_map.shape
        
        if x < 1 or x >= width - 1 or y < 1 or y >= height - 1:
            return 0.0
        
        # Sobel operator
        gx = (
            -1 * depth_map[y-1, x-1] + 1 * depth_map[y-1, x+1] +
            -2 * depth_map[y, x-1]   + 2 * depth_map[y, x+1] +
            -1 * depth_map[y+1, x-1] + 1 * depth_map[y+1, x+1]
        )
        
        gy = (
            -1 * depth_map[y-1, x-1] - 2 * depth_map[y-1, x] - 1 * depth_map[y-1, x+1] +
             1 * depth_map[y+1, x-1] + 2 * depth_map[y+1, x] + 1 * depth_map[y+1, x+1]
        )
        
        return float(np.sqrt(gx * gx + gy * gy) / 8.0)  # Normalize
    
    def _calculate_direction(self, x: float, y: float, width: int, height: int) -> str:
        """Calculate direction relative to center"""
        center_x = width / 2.0
        offset_x = x - center_x
        
        if abs(offset_x) < width * 0.2:
            return "center"
        elif offset_x < 0:
            return "left"
        else:
            return "right"
    
    def _calculate_angle(self, x: float, y: float, width: int, height: int) -> float:
        """Calculate angle in degrees"""
        center_x = width / 2.0
        center_y = height / 2.0
        offset_x = x - center_x
        offset_y = y - center_y
        
        angle_rad = np.arctan2(offset_x, abs(offset_y))
        return float(angle_rad * 180.0 / np.pi)
    
    def analyze_labeled_objects(self, depth_map: np.ndarray, labeled_objects: List[Dict]) -> List[Dict]:
        """
        Main collision analysis method - analyzes labeled objects with bboxes
        
        Args:
            depth_map: 2D numpy array of normalized inverse depth map from MiDaS [0,1]
            labeled_objects: List of labeled objects with bboxes from YOLO/detection system
                Each object should have: objectId, label, bbox [x1, y1, x2, y2], detectionConfidence
        
        Returns:
            List of analyzed objects with danger levels
        """
        results = []
        
        if not labeled_objects:
            return results
        
        # 1. Analyze the scene to understand context
        scene = self.analyze_scene(depth_map)
        
        # 2. Analyze each labeled object for collision threat
        for labeled_obj in labeled_objects:
            obj = self.analyze_labeled_object(depth_map, labeled_obj, scene)
            
            # 3. Calculate collision danger
            danger_info = self.calculate_danger_level(obj, scene, depth_map)
            obj.update(danger_info)
            
            # 4. Add to results (include all objects, even if SAFE, for complete analysis)
            results.append(obj)
        
        # 5. Sort by danger level (most dangerous first)
        danger_order = {
            'CRITICAL_COLLISION': 4,
            'HIGH_WARNING': 3,
            'MODERATE_WARNING': 2,
            'LOW_WARNING': 1,
            'SAFE': 0
        }
        results.sort(key=lambda x: danger_order.get(x['dangerLevel'], 0), reverse=True)
        
        return results


# Global service instance
_collision_detector_instance: Optional[CollisionDetectorService] = None


def get_collision_detector() -> CollisionDetectorService:
    """Get or create global collision detector instance"""
    global _collision_detector_instance
    if _collision_detector_instance is None:
        _collision_detector_instance = CollisionDetectorService()
    return _collision_detector_instance


def collision_analyze(depth_map: np.ndarray, labeled_objects: List[Dict]) -> List[Dict]:
    """
    Analyze collision threats from depth map and labeled objects
    
    Args:
        depth_map: 2D numpy array of normalized depth values
        labeled_objects: List of labeled objects with bboxes
        
    Returns:
        List of analyzed objects with danger levels
    """
    detector = get_collision_detector()
    return detector.analyze_labeled_objects(depth_map, labeled_objects)
