#!/usr/bin/env python3
"""Integration test: fails_count incrementation via task_features_checker.py"""

import json
import subprocess
import tempfile
from pathlib import Path


def test_fails_count_incremented_on_constraint_failure():
    """Test that fails_count is incremented when constraint fails."""
    # Create temporary directory for test files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create temporary task.k.json with a failing constraint
        task_data = {
            "type": "Task",
            "model_version": 2,
            "id": "test_task",
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
        }

        task_path = tmpdir / "task.k.json"
        checks_path = tmpdir / "checks_results.k.json"

        # Write temporary task
        task_path.write_text(json.dumps(task_data, indent=2))

        # Run task_features_checker.py
        result = subprocess.run(
            [
                'python3',
                'constraints_tool/constraints_tool/task_features_checker.py',
                str(task_path),
                '--output-checks-path', str(checks_path)
            ],
            cwd='/project'
        )

        # Verify constraint failed (non-zero exit)
        assert result.returncode == 2, "Expected constraints to fail"

        # Read updated task
        updated_task = json.loads(task_path.read_text())

        # Verify fails_count was incremented
        constraint = updated_task["spec"]["features"]["test_feature"]["constraints"]["test_constraint_fail"]
        assert constraint["fails_count"] == 1, f"Expected fails_count=1, got {constraint['fails_count']}"

        # Verify checks_results.k.json was created
        assert checks_path.exists(), "checks_results.k.json not created"

        print("✓ fails_count successfully incremented on constraint failure")


def test_fails_count_not_incremented_on_passing_constraint():
    """Test that fails_count is NOT incremented when constraint passes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create temporary task.k.json with a passing constraint
        task_data = {
            "type": "Task",
            "model_version": 2,
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

        task_path = tmpdir / "task.k.json"
        checks_path = tmpdir / "checks_results.k.json"

        # Write temporary task
        task_path.write_text(json.dumps(task_data, indent=2))

        # Run task_features_checker.py
        result = subprocess.run(
            [
                'python3',
                'constraints_tool/constraints_tool/task_features_checker.py',
                str(task_path),
                '--output-checks-path', str(checks_path)
            ],
            cwd='/project'
        )

        # Verify constraint passed (exit code 0)
        assert result.returncode == 0, "Expected constraints to pass"

        # Read task (should be unchanged)
        updated_task = json.loads(task_path.read_text())

        # Verify fails_count was NOT incremented (still 0)
        constraint = updated_task["spec"]["features"]["test_feature"]["constraints"]["test_constraint_pass"]
        assert constraint["fails_count"] == 0, f"Expected fails_count=0, got {constraint['fails_count']}"

        print("✓ fails_count NOT incremented on passing constraint")


if __name__ == "__main__":
    test_fails_count_incremented_on_constraint_failure()
    test_fails_count_not_incremented_on_passing_constraint()
    print("\n✅ All fails_count integration tests passed")
