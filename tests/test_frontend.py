"""
Test frontend files for syntax errors and required elements.
"""
import os
import sys
import re
import json
import subprocess
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_js_syntax(file_path: Path) -> tuple:
    """Parse JavaScript with Node; delimiter counts are not syntax validation."""
    executable = shutil.which("node") or shutil.which("nodejs") or shutil.which("node.exe")
    if not executable:
        return False, "Node.js is required for JavaScript syntax checks"
    try:
        # stdin also works when WSL finds a Windows Node executable.
        result = subprocess.run([executable, "--check"],
                                input=file_path.read_text(encoding="utf-8"),
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    return result.returncode == 0, (result.stderr.strip() or "JavaScript parsed successfully")


def check_js_globals(file_path: Path, required_globals: list) -> tuple:
    """Check that required global objects/functions exist."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        missing = []
        for g in required_globals:
            # Check for "const G = {" or "function G(" or "class G"
            patterns = [
                rf'\bconst\s+{g}\s*=',
                rf'\blet\s+{g}\s*=',
                rf'\bvar\s+{g}\s*=',
                rf'\bfunction\s+{g}\s*\(',
                rf'\bclass\s+{g}\s*[{{]',
            ]
            found = any(re.search(p, content) for p in patterns)
            if not found:
                missing.append(g)

        if missing:
            return False, f"Missing globals: {', '.join(missing)}"

        return True, f"All {len(required_globals)} globals found"

    except Exception as e:
        return False, str(e)


def check_css_syntax(file_path: Path) -> tuple:
    """Check CSS file for basic syntax errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check balanced braces
        open_braces = content.count('{')
        close_braces = content.count('}')

        if open_braces != close_braces:
            return False, f"Unbalanced braces: {open_braces} {{ vs {close_braces} }}"

        return True, f"{len(content)} bytes, syntax OK"

    except Exception as e:
        return False, str(e)


def check_html_structure(file_path: Path, required_elements: list) -> tuple:
    """Check HTML file for required elements."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        missing = []
        for elem in required_elements:
            if elem not in content:
                missing.append(elem)

        if missing:
            return False, f"Missing elements: {', '.join(missing[:5])}"

        return True, f"All {len(required_elements)} elements found"

    except Exception as e:
        return False, str(e)


def _check_app_js() -> tuple:
    """Test static/js/app.js"""
    path = Path(__file__).parent.parent / "static/js/app.js"
    if not path.exists():
        return False, "File not found"

    success, msg = check_js_syntax(path)
    if not success:
        return False, msg

    success, msg = check_js_globals(path, ["App"])
    return success, msg


def _check_canvas_js() -> tuple:
    """Test static/js/canvas.js"""
    path = Path(__file__).parent.parent / "static/js/canvas.js"
    if not path.exists():
        return False, "File not found"

    success, msg = check_js_syntax(path)
    if not success:
        return False, msg

    success, msg = check_js_globals(path, ["Canvas"])
    return success, msg


def _check_charts_js() -> tuple:
    """Test static/js/charts.js"""
    path = Path(__file__).parent.parent / "static/js/charts.js"
    if not path.exists():
        return False, "File not found"

    success, msg = check_js_syntax(path)
    if not success:
        return False, msg

    success, msg = check_js_globals(path, ["Charts"])
    return success, msg


def _check_analytics_js() -> tuple:
    """Test static/js/analytics.js"""
    path = Path(__file__).parent.parent / "static/js/analytics.js"
    if not path.exists():
        return False, "File not found"

    success, msg = check_js_syntax(path)
    if not success:
        return False, msg

    success, msg = check_js_globals(path, ["Analytics"])
    return success, msg


def _check_ai_agent_js() -> tuple:
    """Test static/js/ai-agent.js"""
    path = Path(__file__).parent.parent / "static/js/ai-agent.js"
    if not path.exists():
        return False, "File not found"

    success, msg = check_js_syntax(path)
    if not success:
        return False, msg

    success, msg = check_js_globals(path, ["AIAgent"])
    return success, msg


def _check_simulation_js() -> tuple:
    """Test static/js/simulation.js"""
    path = Path(__file__).parent.parent / "static/js/simulation.js"
    if not path.exists():
        return False, "File not found"

    success, msg = check_js_syntax(path)
    if not success:
        return False, msg

    success, msg = check_js_globals(path, ["Simulation"])
    return success, msg


def _check_llm_interface_js() -> tuple:
    """Test static/js/llm-interface.js"""
    path = Path(__file__).parent.parent / "static/js/llm-interface.js"
    if not path.exists():
        return False, "File not found"

    success, msg = check_js_syntax(path)
    if not success:
        return False, msg

    success, msg = check_js_globals(path, ["LLMInterface"])
    return success, msg


def _check_style_css() -> tuple:
    """Test static/css/style.css"""
    path = Path(__file__).parent.parent / "static/css/style.css"
    if not path.exists():
        return False, "File not found"

    return check_css_syntax(path)


def _check_analytics_css() -> tuple:
    """Test static/css/analytics.css"""
    path = Path(__file__).parent.parent / "static/css/analytics.css"
    if not path.exists():
        return False, "File not found"

    return check_css_syntax(path)


def _check_index_html() -> tuple:
    """Test static/index.html for required elements."""
    path = Path(__file__).parent.parent / "static/index.html"
    if not path.exists():
        return False, "File not found"

    required = [
        'id="canvas-container"',
        'id="chart-container"',
        'id="analytics-container"',
        'id="ai-agent-container"',
        'charts.js',
        'analytics.js',
        'ai-agent.js',
        'analytics.css',
        'd3.v7.min.js',
    ]

    return check_html_structure(path, required)


def test_app_js():
    success, message = _check_app_js()
    assert success, message

def test_canvas_js():
    success, message = _check_canvas_js()
    assert success, message

def test_charts_js():
    success, message = _check_charts_js()
    assert success, message

def test_analytics_js():
    success, message = _check_analytics_js()
    assert success, message

def test_ai_agent_js():
    success, message = _check_ai_agent_js()
    assert success, message

def test_simulation_js():
    success, message = _check_simulation_js()
    assert success, message

def test_llm_interface_js():
    success, message = _check_llm_interface_js()
    assert success, message

def test_style_css():
    success, message = _check_style_css()
    assert success, message

def test_analytics_css():
    success, message = _check_analytics_css()
    assert success, message

def test_index_html():
    success, message = _check_index_html()
    assert success, message


def test_js_parser_rejects_balanced_invalid_syntax(tmp_path):
    script = tmp_path / "invalid.js"
    script.write_text("const broken = ;", encoding="utf-8")
    success, message = check_js_syntax(script)
    assert not success
    assert "SyntaxError" in message


def run_all_frontend_tests() -> dict:
    """Run all frontend tests and return results."""
    tests = [
        ("app.js", _check_app_js),
        ("canvas.js", _check_canvas_js),
        ("charts.js", _check_charts_js),
        ("analytics.js", _check_analytics_js),
        ("ai-agent.js", _check_ai_agent_js),
        ("simulation.js", _check_simulation_js),
        ("llm-interface.js", _check_llm_interface_js),
        ("style.css", _check_style_css),
        ("analytics.css", _check_analytics_css),
        ("index.html", _check_index_html),
    ]

    results = []
    passed = 0
    failed = 0

    for name, test_func in tests:
        success, message = test_func()
        results.append({
            "name": name,
            "success": success,
            "message": message
        })

        if success:
            passed += 1
            print(f"PASS: {name} - {message}")
        else:
            failed += 1
            print(f"FAIL: {name} - {message}")

    return {
        "passed": passed,
        "failed": failed,
        "total": len(tests),
        "results": results
    }


if __name__ == "__main__":
    print("=" * 50)
    print("FRONTEND TESTS")
    print("=" * 50)

    results = run_all_frontend_tests()

    print("-" * 50)
    print(f"Frontend: {results['passed']}/{results['total']} passing")

    if results['failed'] > 0:
        print("\nFAILURES:")
        for r in results['results']:
            if not r['success']:
                print(f"  - {r['name']}: {r['message']}")
        sys.exit(1)
    else:
        sys.exit(0)
