"""
Voice Command Handler Module for PiCar-X Robot
Processes voice commands and translates them into robot actions.
"""

import re
import math
import threading
from typing import Optional, Dict, Callable, Tuple
import speech_recognition as sr
from robot_hat import TTS

from .navigation_module import NavigationController, MovementCommand

class VoiceCommandHandler:
    def __init__(self, navigation_controller: NavigationController):
        """
        Initialize the voice command handler.
        
        Args:
            navigation_controller: The robot's navigation controller
        """
        self._nav = navigation_controller
        self._is_listening = False
        self._command_thread = None
        
        # Initialize TTS
        self._tts = TTS()
        self._tts.lang("en-US")
        
        # Wake word to activate commands
        self._wake_word = "robot"
        
        # Command definitions with regex patterns
        self._commands = {
            'stop': {
                'patterns': [
                    r'stop',
                    r'halt',
                    r'freeze'
                ],
                'handler': self._handle_stop
            },
            'move': {
                'patterns': [
                    r'(?:move|go) forward(?: (\d+) centimeters)?',
                    r'(?:move|go) backward(?: (\d+) centimeters)?'
                ],
                'handler': self._handle_move
            },
            'turn': {
                'patterns': [
                    r'turn (?:left|right)(?: (\d+) degrees)?',
                    r'rotate (?:left|right)(?: (\d+) degrees)?'
                ],
                'handler': self._handle_turn
            },
            'explore': {
                'patterns': [
                    r'explore',
                    r'start exploration',
                    r'begin mapping'
                ],
                'handler': self._handle_explore
            },
            'status': {
                'patterns': [
                    r'status',
                    r'what is your status',
                    r'where are you'
                ],
                'handler': self._handle_status
            }
        }
        
        # Initialize speech recognition
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = 4000  # Adjust based on environment
        
        # Response templates
        self._responses = {
            'wake_word': "Yes, I'm listening",
            'command_success': "Command executed successfully",
            'command_failed': "Sorry, I couldn't execute that command",
            'not_understood': "Sorry, I didn't understand that command",
            'exploring': "Starting exploration mode",
            'stopping': "Stopping all movements"
        }

    def start_listening(self):
        """Start listening for voice commands in a background thread."""
        if self._command_thread is None or not self._command_thread.is_alive():
            self._is_listening = True
            self._command_thread = threading.Thread(target=self._listening_loop)
            self._command_thread.daemon = True
            self._command_thread.start()
            return True
        return False

    def stop_listening(self):
        """Stop listening for voice commands."""
        self._is_listening = False
        if self._command_thread:
            self._command_thread.join()

    def _speak(self, text: str):
        """
        Speak the given text using TTS.
        
        Args:
            text: Text to speak
        """
        try:
            self._tts.say(text)
        except Exception as e:
            print(f"TTS Error: {e}")
            # Fallback to print if TTS fails
            print(text)

    def _listening_loop(self):
        """Background thread function for continuous command processing."""
        with sr.Microphone() as source:
            # Adjust for ambient noise
            self._recognizer.adjust_for_ambient_noise(source, duration=1)
            
            while self._is_listening:
                try:
                    # Listen for audio input
                    audio = self._recognizer.listen(source, timeout=1, phrase_time_limit=5)
                    
                    # Convert to text
                    text = self._recognizer.recognize_google(audio).lower()
                    print(f"Heard: {text}")
                    
                    # Check for wake word
                    if self._wake_word in text:
                        self._speak(self._responses['wake_word'])
                        continue
                    
                    # Process command
                    success = self._process_command(text)
                    if success:
                        self._speak(self._responses['command_success'])
                    else:
                        self._speak(self._responses['not_understood'])
                        
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    # Speech was unintelligible
                    continue
                except Exception as e:
                    print(f"Error in voice command processing: {e}")
                    continue

    def _process_command(self, text: str) -> bool:
        """
        Process a voice command.
        
        Args:
            text: The command text to process
            
        Returns:
            bool: True if command was processed successfully
        """
        for command_type, command_info in self._commands.items():
            for pattern in command_info['patterns']:
                match = re.search(pattern, text)
                if match:
                    return command_info['handler'](match)
        return False

    def _handle_stop(self, match) -> bool:
        """Handle stop command."""
        self._speak(self._responses['stopping'])
        return self._nav.stop()

    def _handle_move(self, match) -> bool:
        """Handle movement command."""
        try:
            # Extract distance if provided
            distance = int(match.group(1)) if match.group(1) else 50  # Default 50cm
            
            # Check if backward
            is_backward = 'backward' in match.group(0)
            
            if is_backward:
                # TODO: Implement backward movement
                self._speak("Backward movement not yet implemented")
                return False
            else:
                # Move forward
                self._speak(f"Moving forward {distance} centimeters")
                self._nav.move_forward(self._nav._max_speed/2)
                return True
        except Exception as e:
            print(f"Error in move command: {e}")
            return False

    def _handle_turn(self, match) -> bool:
        """Handle turn command."""
        try:
            # Extract degrees if provided
            degrees = int(match.group(1)) if match.group(1) else 90  # Default 90 degrees
            
            # Convert to radians
            angle = math.radians(degrees)
            
            # Determine direction
            is_right = 'right' in match.group(0)
            if is_right:
                angle = -angle
                self._speak(f"Turning right {degrees} degrees")
            else:
                self._speak(f"Turning left {degrees} degrees")
                
            return self._nav.turn(angle)
        except Exception as e:
            print(f"Error in turn command: {e}")
            return False

    def _handle_explore(self, match) -> bool:
        """Handle exploration command."""
        try:
            self._speak(self._responses['exploring'])
            
            # Find nearest frontier
            frontier = self._nav.find_nearest_frontier()
            if frontier:
                return self._nav.navigate_to_point(frontier[0], frontier[1])
            self._speak("No unexplored areas found")
            return False
        except Exception as e:
            print(f"Error in explore command: {e}")
            return False

    def _handle_status(self, match) -> bool:
        """Handle status request command."""
        try:
            pose = self._nav.get_pose()
            status_msg = (f"Current position: {pose.x:.1f} centimeters forward, "
                         f"{pose.y:.1f} centimeters left, facing {math.degrees(pose.theta):.1f} degrees")
            self._speak(status_msg)
            return True
        except Exception as e:
            print(f"Error in status command: {e}")
            return False

    def add_custom_command(self, name: str, patterns: list, handler: Callable):
        """
        Add a custom voice command.
        
        Args:
            name: Name of the command
            patterns: List of regex patterns to match
            handler: Function to handle the command
        """
        self._commands[name] = {
            'patterns': patterns,
            'handler': handler
        }

    def set_wake_word(self, word: str):
        """
        Set a new wake word.
        
        Args:
            word: New wake word to use
        """
        self._wake_word = word.lower()

    def get_available_commands(self) -> Dict[str, list]:
        """
        Get list of available commands and their patterns.
        
        Returns:
            dict: Dictionary of command names and their patterns
        """
        return {name: info['patterns'] for name, info in self._commands.items()}
