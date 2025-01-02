"""
ChatGPT Integration Module for PiCar-X Robot
Handles interactions with OpenAI's ChatGPT API for intelligent responses and analysis.
"""

import os
import base64
import time
from typing import Optional, Dict, List, Any, Tuple
import requests
from openai import OpenAI
import cv2
import numpy as np

class ChatGPTClient:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the ChatGPT client.
        
        Args:
            api_key: OpenAI API key (optional, can be set via environment variable)
        """
        self._api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self._api_key:
            raise ValueError("OpenAI API key must be provided or set in OPENAI_API_KEY environment variable")
            
        self._client = OpenAI(api_key=self._api_key)
        
        # Rate limiting settings
        self._last_request_time = 0
        self._min_request_interval = 1.0  # Minimum seconds between requests
        
        # Context management
        self._conversation_history: List[Dict[str, str]] = []
        self._max_history_length = 10
        
        # Response templates
        self._system_prompt = """You are an AI assistant for a PiCar-X robot. 
        You help interpret sensor data, provide navigation suggestions, and explain the robot's behavior.
        Keep responses concise and focused on the robot's operation."""

    def send_sensor_data(self, sensor_data: Dict[str, Any]) -> str:
        """
        Send sensor data to ChatGPT for analysis.
        
        Args:
            sensor_data: Dictionary containing sensor readings
            
        Returns:
            str: ChatGPT's analysis and commentary
        """
        # Format sensor data into a prompt
        prompt = self._format_sensor_data(sensor_data)
        
        return self._send_message(prompt)

    def send_image_for_analysis(self, image: np.ndarray) -> str:
        """
        Send an image to ChatGPT for analysis.
        
        Args:
            image: OpenCV image array
            
        Returns:
            str: ChatGPT's analysis of the image
        """
        # Convert image to base64
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Create message with image
        messages = [
            {"role": "system", "content": self._system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please analyze this image from the robot's camera and describe what you see, "
                               "focusing on obstacles, paths, and anything relevant for navigation."
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{image_base64}"
                    }
                ]
            }
        ]
        
        try:
            # Respect rate limiting
            self._wait_for_rate_limit()
            
            # Make API call
            response = self._client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=messages,
                max_tokens=300
            )
            
            self._last_request_time = time.time()
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error in image analysis: {e}")
            return "Error analyzing image"

    def get_navigation_advice(self, 
                            current_pose: Dict[str, float],
                            obstacle_data: Dict[str, Any],
                            target: Optional[Dict[str, float]] = None) -> str:
        """
        Get navigation advice based on current situation.
        
        Args:
            current_pose: Robot's current position and orientation
            obstacle_data: Information about nearby obstacles
            target: Optional target position
            
        Returns:
            str: Navigation advice from ChatGPT
        """
        # Format situation into a prompt
        prompt = f"The robot is at position (x={current_pose['x']:.1f}, y={current_pose['y']:.1f}) "
        prompt += f"facing {current_pose['theta']:.1f} degrees.\n"
        
        if obstacle_data:
            prompt += "Nearby obstacles:\n"
            for direction, distance in obstacle_data.items():
                prompt += f"- {direction}: {distance:.1f} cm\n"
        
        if target:
            prompt += f"\nTarget position is (x={target['x']:.1f}, y={target['y']:.1f}).\n"
            
        prompt += "\nWhat would you advise for navigation?"
        
        return self._send_message(prompt)

    def get_exploration_strategy(self, 
                               explored_area_percentage: float,
                               frontier_points: List[Tuple[float, float]]) -> str:
        """
        Get strategic advice for exploration.
        
        Args:
            explored_area_percentage: Percentage of area explored
            frontier_points: List of frontier points for exploration
            
        Returns:
            str: Strategic advice from ChatGPT
        """
        prompt = f"The robot has explored {explored_area_percentage:.1f}% of the area.\n"
        prompt += f"There are {len(frontier_points)} frontier points available for exploration.\n"
        prompt += "What strategy would you recommend for efficient exploration?"
        
        return self._send_message(prompt)

    def _format_sensor_data(self, sensor_data: Dict[str, Any]) -> str:
        """Format sensor data into a prompt for ChatGPT."""
        prompt = "Current sensor readings:\n"
        
        for sensor_type, value in sensor_data.items():
            if isinstance(value, (int, float)):
                prompt += f"- {sensor_type}: {value:.2f}\n"
            else:
                prompt += f"- {sensor_type}: {value}\n"
                
        prompt += "\nWhat insights can you provide about these readings?"
        return prompt

    def _send_message(self, message: str) -> str:
        """
        Send a message to ChatGPT and get response.
        
        Args:
            message: Message to send
            
        Returns:
            str: ChatGPT's response
        """
        try:
            # Respect rate limiting
            self._wait_for_rate_limit()
            
            # Prepare messages with conversation history
            messages = [{"role": "system", "content": self._system_prompt}]
            messages.extend(self._conversation_history)
            messages.append({"role": "user", "content": message})
            
            # Make API call
            response = self._client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=150,
                temperature=0.7
            )
            
            # Update rate limiting and conversation history
            self._last_request_time = time.time()
            self._update_conversation_history(message, response.choices[0].message.content)
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error in ChatGPT communication: {e}")
            return "Error communicating with ChatGPT"

    def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)

    def _update_conversation_history(self, user_message: str, assistant_response: str):
        """Update conversation history, maintaining maximum length."""
        self._conversation_history.append({"role": "user", "content": user_message})
        self._conversation_history.append({"role": "assistant", "content": assistant_response})
        
        # Trim history if too long
        if len(self._conversation_history) > self._max_history_length * 2:
            self._conversation_history = self._conversation_history[-self._max_history_length * 2:]

    def clear_conversation_history(self):
        """Clear the conversation history."""
        self._conversation_history = []
