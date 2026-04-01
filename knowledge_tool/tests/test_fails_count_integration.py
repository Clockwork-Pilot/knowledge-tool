#!/usr/bin/env python3
"""Integration test: fails_count incrementation via check_spec_constraints.py

Note: Tests are skipped - constraint_checker needs update for Spec documents (spec decoupling refactor).
"""

import json
import subprocess
import tempfile
from pathlib import Path
import pytest


@pytest.mark.skip(reason="constraint_checker needs Spec document support (spec decoupling)")
def test_fails_count_incremented_on_constraint_failure():
    """Test that fails_count is incremented when constraint fails (now in task-spec.k.json)."""
    # Create temporary directory for test files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create temporary task-spec.k.json with a failing constraint
        spec_data = {
            "type": "Spec",
            "model_version": 1,
            "version": 1,
            "description": "Test specification",
            "features": {
                "test_feature": {
                    "type": "Feature",
                    "model_version": 1,
                    "id": "test_feature",
                    "description": "Test feature with failing constraint",
                    "constraints": {
                        "test_constraint_fail": {
                            "id": "test_constraint_fail",
                            "cmd": "test -f /nonexistent/file.txt && echo 'found' || { echo 'not found'; exit 1; }",
                            "tags": [],
                            "description": "This constraint will fail",
                            "fails_count": 0
                        }
                    }
                }
            }
        }

        spec_path = tmpdir / "task-spec.k.json"
        checks_path = tmpdir / "task-results.k.json"

        # Write temporary spec
        spec_path.write_text(json.dumps(spec_data, indent=2))

        # Run check_spec_constraints.py on spec
        result = subprocess.run(
            [
                'python3',
                'constraints_tool/constraints_tool/check_spec_constraints.py',
                str(spec_path),
                '--output-checks-path', str(checks_path)
            ],
            cwd='/project'
        )

        # Verify constraint failed (non-zero exit)
        assert result.returncode == 2, "Expected constraints to fail"

        # Read updated spec
        updated_spec = json.loads(spec_path.read_text())

        # Verify fails_count was incremented
        constraint = updated_spec["features"]["test_feature"]["constraints"]["test_constraint_fail"]
        assert constraint["fails_count"] == 1, f"Expected fails_count=1, got {constraint['fails_count']}"

        # Verify task-results.k.json was created
        assert checks_path.exists(), "task-results.k.json not created"

        print("✓ fails_count successfully incremented on constraint failure")


@pytest.mark.skip(reason="constraint_checker needs Spec document support (spec decoupling)")
def test_fails_count_not_incremented_on_passing_constraint():
    """Test that fails_count is NOT incremented when constraint passes (now in task-spec.k.json)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create temporary task-spec.k.json with a passing constraint
        spec_data = {
            "type": "Spec",
            "model_version": 1,
            "id": "test_task_pass",
            "spec": {
                "type": "Spec",
                "model_version": 1,
                "version": 1,
                "description": "Test task",
                "features": {
                    "test_feature": {
                        "type": "Feature",
                        "model_version": 1,
                        "id": "test_feature",
                        "description": "Test feature with passing constraint",
                        "constraints": {
                            "test_constraint_pass": {
                                "id": "test_constraint_pass",
                                "cmd": "test -f /etc/hostname && echo 'found' || { echo 'not found'; exit 1; }",
                                "tags": [],
                                "description": "This constraint will pass",
                                "fails_count": 0
                            }
                        }
                    }
                }
            }
        }

        spec_path = tmpdir / "task-spec.k.json"
        checks_path = tmpdir / "task-results.k.json"

        # Write temporary task
        spec_path.write_text(json.dumps(spec_data, indent=2))

        # Run check_spec_constraints.py
        result = subprocess.run(
            [
                'python3',
                'constraints_tool/constraints_tool/check_spec_constraints.py',
                str(spec_path),
                '--output-checks-path', str(checks_path)
            ],
            cwd='/project'
        )

        # Verify constraint passed (exit code 0)
        assert result.returncode == 0, "Expected constraints to pass"

        # Read task (should be unchanged)
        updated_spec = json.loads(spec_path.read_text())

        # Verify fails_count was NOT incremented (still 0)
        constraint = updated_spec["features"]["test_feature"]["constraints"]["test_constraint_pass"]
        assert constraint["fails_count"] == 0, f"Expected fails_count=0, got {constraint['fails_count']}"

        print("✓ fails_count NOT incremented on passing constraint")


if __name__ == "__main__":
    test_fails_count_incremented_on_constraint_failure()
    test_fails_count_not_incremented_on_passing_constraint()
    print("\n✅ All fails_count integration tests passed")
