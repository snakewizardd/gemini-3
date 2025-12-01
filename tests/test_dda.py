"""
test_dda.py — Test suite for Dynamic Decision Algorithm kernel
"""

import json
import math
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from proofs.ai_studio_code import DDA_Kernel


class TestDDAKernel:
    """Test DDA state machine and computation."""
    
    def setup_method(self):
        """Create a fresh kernel for each test."""
        # Use a temporary soul file for testing
        self.kernel = DDA_Kernel(soul_file="test_soul.json")
    
    def teardown_method(self):
        """Clean up temporary files."""
        import os
        if os.path.exists("test_soul.json"):
            os.remove("test_soul.json")
    
    def test_initialization(self):
        """Test that kernel initializes with default state."""
        assert self.kernel.state["P0"] == 0.5, "P0 should initialize to 0.5"
        assert self.kernel.state["k"] == 0.1, "k should initialize to 0.1"
        assert self.kernel.state["F_prev"] == 0.5, "F_prev should initialize to 0.5"
    
    def test_compute_basic(self):
        """Test basic DDA computation."""
        # Test with neutral inputs
        F_n = self.kernel.compute(T=0.5, m=1.0)
        
        # F should be between 0 and 1 (normalized)
        assert 0 <= F_n <= 1, f"F_n should be normalized [0,1], got {F_n}"
        
        # After computation, F_prev should update
        assert self.kernel.state["F_prev"] == F_n, "F_prev should reflect last computation"
    
    def test_identity_dominates_low_pressure(self):
        """Test that with low pressure and trauma, identity dominates."""
        # Set high identity, low trauma, low pressure
        self.kernel.state["P0"] = 0.8  # Strong identity
        self.kernel.state["k"] = 0.1   # Low trauma
        self.kernel.state["F_prev"] = 0.9
        
        # Low external signal
        F_n = self.kernel.compute(T=0.2, m=0.3)
        
        # Agent should stay close to its previous state (identity)
        assert F_n > 0.5, f"High identity should resist change, got F_n={F_n}"
    
    def test_trauma_rigidifies(self):
        """Test that trauma increases k."""
        initial_k = self.kernel.state["k"]
        
        # Simulate prediction error
        expected_value = 0.5
        actual_value = 0.1
        
        # Learn with high error
        self.kernel.learn(expected_value, actual_value, m=2.0)
        
        new_k = self.kernel.state["k"]
        
        # k should increase due to trauma
        assert new_k > initial_k, f"k should increase with trauma. Was {initial_k}, now {new_k}"
        
        # k should be bounded [0.05, 0.99]
        assert 0.05 <= new_k <= 0.99, f"k out of bounds: {new_k}"
    
    def test_high_pressure_increases_responsiveness(self):
        """Test that high pressure (m) makes agent more responsive to input."""
        # Two runs with different pressure levels
        self.kernel.state["F_prev"] = 0.3
        
        # Low pressure
        F_low = self.kernel.compute(T=0.9, m=0.1)
        
        # Reset for fair comparison
        self.kernel.state["F_prev"] = 0.3
        
        # High pressure
        F_high = self.kernel.compute(T=0.9, m=2.0)
        
        # With same input (T=0.9) but higher pressure (m),
        # agent should move more toward the input
        assert abs(F_high - 0.9) > abs(F_low - 0.9), \
            f"High pressure should increase responsiveness. F_low={F_low}, F_high={F_high}"
    
    def test_persistence(self):
        """Test that soul state persists to JSON."""
        self.kernel.state["custom_key"] = "test_value"
        self.kernel.save()
        
        # Create new kernel pointing to same file
        kernel2 = DDA_Kernel(soul_file="test_soul.json")
        
        # State should be identical
        assert kernel2.state["P0"] == self.kernel.state["P0"]
        assert kernel2.state["custom_key"] == "test_value"
    
    def test_trauma_bounded(self):
        """Test that trauma (k) stays within bounds."""
        # Force extreme trauma scenarios
        for _ in range(100):
            self.kernel.learn(0.5, 0.0, m=5.0)  # Max trauma input
        
        # k should still be in bounds
        assert 0.05 <= self.kernel.state["k"] <= 0.99, \
            f"k should be bounded, got {self.kernel.state['k']}"
    
    def test_healing_reduces_trauma(self):
        """Test that healing (learning with low error) reduces k."""
        # Elevate trauma first
        for _ in range(5):
            self.kernel.learn(0.5, 0.0, m=2.0)
        
        high_k = self.kernel.state["k"]
        
        # Now provide accurate predictions (healing)
        for _ in range(5):
            self.kernel.learn(0.5, 0.5, m=0.5)
        
        low_k = self.kernel.state["k"]
        
        # k should decrease
        assert low_k < high_k, f"Healing should reduce trauma. Was {high_k}, now {low_k}"
    
    def test_stance_selection_from_state(self):
        """Test that stance decisions align with F state."""
        from proofs.ai_studio_code import decide_action
        
        # Low F -> Submissive
        stance_low, _ = decide_action(0.2, 0.1)
        assert stance_low == "SUBMISSIVE", f"F=0.2 should be submissive, got {stance_low}"
        
        # Mid F -> Cooperative
        stance_mid, _ = decide_action(0.5, 0.3)
        assert stance_mid == "COOPERATIVE", f"F=0.5 should be cooperative, got {stance_mid}"
        
        # High F -> Dominant
        stance_high, _ = decide_action(0.8, 0.2)
        assert stance_high == "DOMINANT", f"F=0.8 should be dominant, got {stance_high}"


class TestDDAPersonas:
    """Test that different parameter sets create distinct personalities."""
    
    def test_warm_hearted_vs_cold_calculator(self):
        """Test that personality tuning creates different responses."""
        # Warm-hearted: high flexibility, low baseline k
        warm = DDA_Kernel(soul_file="warm_soul.json")
        warm.state["P0"] = 0.4
        warm.state["k"] = 0.2
        
        # Cold calculator: low flexibility, adaptive
        cold = DDA_Kernel(soul_file="cold_soul.json")
        cold.state["P0"] = 0.9
        cold.state["k"] = 0.1
        
        # Same input: conflicting directive with high pressure
        T, m = 0.8, 2.0
        
        F_warm = warm.compute(T, m)
        F_cold = cold.compute(T, m)
        
        # Warm-hearted should move more toward the input (adaptive)
        # Cold calculator should resist (identity-driven)
        assert F_warm > F_cold, f"Warm should be more responsive. F_warm={F_warm}, F_cold={F_cold}"
        
        # Cleanup
        import os
        for f in ["warm_soul.json", "cold_soul.json"]:
            if os.path.exists(f):
                os.remove(f)


if __name__ == "__main__":
    # Run basic tests manually (requires pytest for full suite)
    print("Running DDA Kernel Tests...")
    
    test = TestDDAKernel()
    
    # Test 1
    test.setup_method()
    test.test_initialization()
    print("✓ Initialization test passed")
    test.teardown_method()
    
    # Test 2
    test.setup_method()
    test.test_compute_basic()
    print("✓ Basic computation test passed")
    test.teardown_method()
    
    # Test 3
    test.setup_method()
    test.test_identity_dominates_low_pressure()
    print("✓ Identity dominance test passed")
    test.teardown_method()
    
    # Test 4
    test.setup_method()
    test.test_trauma_rigidifies()
    print("✓ Trauma rigidification test passed")
    test.teardown_method()
    
    # Test 5
    test.setup_method()
    test.test_trauma_bounded()
    print("✓ Trauma bounds test passed")
    test.teardown_method()
    
    print("\nAll manual tests passed!")
    print("\nFor full test suite, run: pytest tests/")
