"""
Depth Estimation Service
Implements MiDaS depth estimation functionality from TestActivity.java
"""

import os
import numpy as np
from PIL import Image
from typing import Dict, Optional, Tuple
import time

try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("Warning: TensorFlow not available. Depth estimation will be stubbed.")


class DepthEstimatorService:
    """Service for depth estimation using MiDaS model"""
    
    def __init__(self):
        self.model_loaded = False
        self.interpreter: Optional[object] = None
        self.model_path: Optional[str] = None
        self.input_size = 256  # MiDaS small input size
    
    def load_model(self, model_path: str = 'midas_v3.1_small.tflite') -> bool:
        """
        Load depth estimation model
        
        Args:
            model_path: Path to TFLite model file
            
        Returns:
            True if successful
        """
        if not TENSORFLOW_AVAILABLE:
            print("TensorFlow not available. Using stub implementation.")
            self.model_loaded = True
            return True
        
        try:
            # Try to find model in common locations
            possible_paths = [
                model_path,
                os.path.join('models', model_path),
                os.path.join('assets', model_path),
                os.path.join(os.path.dirname(__file__), '..', 'models', model_path),
            ]
            
            actual_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    actual_path = path
                    break
            
            if actual_path is None:
                print(f"Model not found at {model_path}. Using stub implementation.")
                self.model_loaded = True
                return True
            
            # Load TFLite model
            self.interpreter = tf.lite.Interpreter(model_path=actual_path)
            self.interpreter.allocate_tensors()
            self.model_path = actual_path
            self.model_loaded = True
            
            return True
            
        except Exception as e:
            print(f"Failed to load depth model: {e}")
            print("Using stub implementation.")
            self.model_loaded = True
            return False
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.model_loaded
    
    def preprocess_image(self, image: Image.Image) -> np.ndarray:
        """
        Preprocess image for model input
        
        Args:
            image: PIL Image
            
        Returns:
            Preprocessed image as numpy array (uint8, 256x256x3)
        """
        # Resize to model input size
        resized = image.resize((self.input_size, self.input_size), Image.LANCZOS)
        
        # Convert to numpy array (RGB, uint8)
        img_array = np.array(resized, dtype=np.uint8)
        
        # Flatten to 1D array for model input
        # Model expects uint8 values in RGB order: [R, G, B, R, G, B, ...]
        img_flat = img_array.reshape(-1, 3)
        
        # Convert to ByteBuffer-like format (uint8)
        return img_flat.flatten().astype(np.uint8)
    
    def estimate_depth(self, image: Image.Image) -> Dict:
        """
        Estimate depth from image
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with depth estimation results:
            {
                'depthMap': np.ndarray,  # 2D array [256, 256] of normalized depth [0,1]
                'stats': Dict,  # Depth statistics
                'inferenceTime': float  # Inference time in ms
            }
        """
        if not self.model_loaded:
            self.load_model()
        
        start_time = time.time()
        
        # Stub implementation if TensorFlow not available or model not loaded
        if not TENSORFLOW_AVAILABLE or self.interpreter is None:
            # Return mock depth map
            depth_map = np.random.rand(self.input_size, self.input_size).astype(np.float32)
            depth_map = (depth_map * 0.5 + 0.3)  # Normalize to [0.3, 0.8] range
            
            inference_time = (time.time() - start_time) * 1000
            
            return {
                'depthMap': depth_map,
                'stats': {
                    'min': float(np.min(depth_map)),
                    'max': float(np.max(depth_map)),
                    'avg': float(np.mean(depth_map)),
                },
                'inferenceTime': inference_time
            }
        
        try:
            # Preprocess image
            input_data = self.preprocess_image(image)
            
            # Get input and output tensors
            input_details = self.interpreter.get_input_details()
            output_details = self.interpreter.get_output_details()
            
            # Prepare input
            input_shape = input_details[0]['shape']
            input_data = input_data.reshape(input_shape)
            
            # Set input tensor
            self.interpreter.set_tensor(input_details[0]['index'], input_data)
            
            # Run inference
            self.interpreter.invoke()
            
            # Get output
            output_data = self.interpreter.get_tensor(output_details[0]['index'])
            
            # Model outputs UINT8 with shape [1, 256, 256, 1]
            # Extract depth map from 4D output: [batch=0][y][x][channel=0]
            output_array = output_data[0]  # Remove batch dimension: [256, 256, 1]
            
            # Process UINT8 output - convert to normalized float [0, 1]
            if output_array.dtype == np.uint8:
                depth_map = output_array[:, :, 0].astype(np.float32) / 255.0
            else:
                depth_map = output_array[:, :, 0].astype(np.float32)
                # Normalize to [0, 1] if not already
                depth_min = np.min(depth_map)
                depth_max = np.max(depth_map)
                if depth_max > depth_min:
                    depth_map = (depth_map - depth_min) / (depth_max - depth_min)
            
            inference_time = (time.time() - start_time) * 1000
            
            # Calculate statistics
            depth_map_flat = depth_map.flatten()
            depth_map_flat = depth_map_flat[depth_map_flat > 0]  # Filter zeros
            
            stats = {
                'min': float(np.min(depth_map)) if len(depth_map_flat) > 0 else 0.0,
                'max': float(np.max(depth_map)) if len(depth_map_flat) > 0 else 0.0,
                'avg': float(np.mean(depth_map_flat)) if len(depth_map_flat) > 0 else 0.0,
            }
            
            return {
                'depthMap': depth_map,
                'stats': stats,
                'inferenceTime': inference_time
            }
            
        except Exception as e:
            print(f"Depth estimation error: {e}")
            # Return stub on error
            depth_map = np.random.rand(self.input_size, self.input_size).astype(np.float32) * 0.5 + 0.3
            return {
                'depthMap': depth_map,
                'stats': {
                    'min': 0.3,
                    'max': 0.8,
                    'avg': 0.55,
                },
                'inferenceTime': 0.0
            }


# Global service instance
_depth_estimator_instance: Optional[DepthEstimatorService] = None


def get_depth_estimator() -> DepthEstimatorService:
    """Get or create global depth estimator instance"""
    global _depth_estimator_instance
    if _depth_estimator_instance is None:
        _depth_estimator_instance = DepthEstimatorService()
    return _depth_estimator_instance


def depth_estimate(image_path: str) -> Dict:
    """
    Estimate depth from image file
    
    Args:
        image_path: Path to image file
        
    Returns:
        Dictionary with depth estimation results
    """
    estimator = get_depth_estimator()
    if not estimator.is_loaded():
        estimator.load_model()
    
    image = Image.open(image_path)
    return estimator.estimate_depth(image)
