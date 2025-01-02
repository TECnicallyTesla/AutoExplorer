"""
Test cases for the System Monitor Module
"""

import unittest
import time
from modules.system_monitor import SystemMonitor

class TestSystemMonitor(unittest.TestCase):
    def setUp(self):
        """Set up test cases."""
        self.monitor = SystemMonitor()

    def tearDown(self):
        """Clean up after tests."""
        self.monitor.release()

    def test_monitoring_start_stop(self):
        """Test that system monitoring can be started and stopped."""
        # Start monitoring
        started = self.monitor.start_monitoring()
        self.assertTrue(started)
        self.assertTrue(self.monitor._is_monitoring)
        self.assertIsNotNone(self.monitor._monitoring_thread)
        self.assertTrue(self.monitor._monitoring_thread.is_alive())
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        time.sleep(0.1)  # Give thread time to stop
        self.assertFalse(self.monitor._is_monitoring)
        self.assertFalse(self.monitor._monitoring_thread.is_alive())

    def test_get_system_stats(self):
        """Test that system statistics are returned in correct format."""
        stats = self.monitor.get_system_stats()
        
        # Check that all required metrics are present
        self.assertIn('battery_level', stats)
        self.assertIn('cpu_percent', stats)
        self.assertIn('temperature', stats)
        
        # Check that values are of correct type
        self.assertIsInstance(stats['battery_level'], (int, float))
        self.assertIsInstance(stats['cpu_percent'], (int, float))
        self.assertIsInstance(stats['temperature'], (int, float))
        
        # Check that values are within reasonable ranges
        self.assertGreaterEqual(stats['battery_level'], 0)
        self.assertLessEqual(stats['battery_level'], 100)
        self.assertGreaterEqual(stats['cpu_percent'], 0)
        self.assertLessEqual(stats['cpu_percent'], 100)
        self.assertGreaterEqual(stats['temperature'], 0)

    def test_check_battery(self):
        """Test battery level checking."""
        battery_level = self.monitor.check_battery()
        
        # Battery level might be None if not available on the system
        if battery_level is not None:
            self.assertIsInstance(battery_level, (int, float))
            self.assertGreaterEqual(battery_level, 0)
            self.assertLessEqual(battery_level, 100)

    def test_monitoring_updates(self):
        """Test that monitoring actually updates the metrics."""
        # Start monitoring
        self.monitor.start_monitoring()
        
        # Get initial values
        initial_stats = self.monitor.get_system_stats()
        
        # Wait for a few monitoring cycles
        time.sleep(self.monitor._monitoring_interval * 2)
        
        # Get updated values
        updated_stats = self.monitor.get_system_stats()
        
        # At least CPU usage should have changed
        self.assertNotEqual(
            initial_stats['cpu_percent'],
            updated_stats['cpu_percent'],
            "CPU usage should change over time"
        )
        
        self.monitor.stop_monitoring()

if __name__ == '__main__':
    unittest.main() 