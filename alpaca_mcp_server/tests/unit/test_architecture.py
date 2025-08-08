"""
Simple architecture tests that don't require external dependencies.
These tests verify the modular structure and basic imports.
"""

from pathlib import Path


class TestProjectStructure:
    """Test the project structure and architecture."""

    def test_project_root_exists(self):
        """Test that project root directory exists."""
        project_root = Path(__file__).parent.parent.parent.parent
        assert project_root.exists()
        assert (project_root / "alpaca_mcp_server").exists()

    def test_server_components_directory_exists(self):
        """Test that server_components directory was created."""
        components_dir = Path(__file__).parent.parent.parent / "server_components"
        assert components_dir.exists()
        assert components_dir.is_dir()

    def test_required_component_files_exist(self):
        """Test that all required component files exist."""
        components_dir = Path(__file__).parent.parent.parent / "server_components"

        required_files = [
            "__init__.py",
            "tool_registrations.py",
            "prompt_registrations.py",
            "resource_registrations.py",
            "server_init.py",
        ]

        for file_name in required_files:
            file_path = components_dir / file_name
            assert file_path.exists(), f"Missing required file: {file_name}"
            assert file_path.is_file(), f"Not a file: {file_name}"

    def test_server_py_is_refactored(self):
        """Test that server.py has been refactored to be much smaller."""
        server_py = Path(__file__).parent.parent.parent / "server.py"
        assert server_py.exists()

        # Read the file and count lines
        with open(server_py) as f:
            lines = f.readlines()

        # Should be much smaller than original (which was 1634 lines)
        assert len(lines) < 200, f"server.py should be refactored to <200 lines, got {len(lines)}"

        # Should be approximately 84 lines as expected
        assert 50 < len(lines) < 150, f"server.py should be ~84 lines, got {len(lines)}"

    def test_component_files_have_content(self):
        """Test that component files are not empty and have expected structure."""
        components_dir = Path(__file__).parent.parent.parent / "server_components"

        # Test tool_registrations.py
        tool_reg_file = components_dir / "tool_registrations.py"
        with open(tool_reg_file) as f:
            content = f.read()

        assert "register_all_tools" in content
        assert "def register_" in content
        assert "@mcp.tool()" in content
        assert len(content.splitlines()) > 100  # Should be substantial

        # Test prompt_registrations.py
        prompt_reg_file = components_dir / "prompt_registrations.py"
        with open(prompt_reg_file) as f:
            content = f.read()

        assert "register_all_prompts" in content
        assert "def register_" in content
        assert "@mcp.prompt()" in content

        # Test resource_registrations.py
        resource_reg_file = components_dir / "resource_registrations.py"
        with open(resource_reg_file) as f:
            content = f.read()

        assert "register_all_resources" in content
        assert "def register_" in content
        assert "@mcp.resource(" in content


class TestRefactoringBenefits:
    """Test that the refactoring achieved its goals."""

    def test_server_py_imports_components(self):
        """Test that server.py imports from the new components."""
        server_py = Path(__file__).parent.parent.parent / "server.py"

        with open(server_py) as f:
            content = f.read()

        # Should import from server_components
        assert (
            "from .server_components import" in content
            or "from alpaca_mcp_server.server_components import" in content
        )
        assert "register_all_tools" in content
        assert "register_all_prompts" in content
        assert "register_all_resources" in content

    def test_separation_of_concerns(self):
        """Test that concerns are properly separated."""
        components_dir = Path(__file__).parent.parent.parent / "server_components"

        # Tool registrations should only contain tool-related code
        with open(components_dir / "tool_registrations.py") as f:
            tool_content = f.read()

        # Should have tools but not prompts or resources
        assert "@mcp.tool()" in tool_content
        assert tool_content.count("@mcp.tool()") > 20  # Many tools
        assert "@mcp.prompt()" not in tool_content  # No prompts in tools file

        # Prompt registrations should only contain prompt-related code
        with open(components_dir / "prompt_registrations.py") as f:
            prompt_content = f.read()

        assert "@mcp.prompt()" in prompt_content
        assert "@mcp.tool()" not in prompt_content  # No tools in prompts file

    def test_modular_functions_exist(self):
        """Test that modular registration functions exist."""
        components_dir = Path(__file__).parent.parent.parent / "server_components"

        # Check tool_registrations.py for category functions
        with open(components_dir / "tool_registrations.py") as f:
            content = f.read()

        expected_functions = [
            "register_account_tools",
            "register_market_data_tools",
            "register_scanner_tools",
            "register_all_tools",
        ]

        for func_name in expected_functions:
            assert f"def {func_name}" in content, f"Missing function: {func_name}"


class TestCIConfiguration:
    """Test that CI/CD configuration is properly set up."""

    def test_github_workflow_exists(self):
        """Test that GitHub Actions workflow exists."""
        workflow_file = (
            Path(__file__).parent.parent.parent.parent / ".github" / "workflows" / "ci.yml"
        )
        assert workflow_file.exists(), "Missing GitHub Actions workflow"

        with open(workflow_file) as f:
            content = f.read()

        # Should have key CI/CD components
        assert "code-quality" in content
        assert "test-unit" in content
        assert "test-integration" in content
        assert "deploy-production" in content

    def test_precommit_config_exists(self):
        """Test that pre-commit configuration exists."""
        precommit_file = Path(__file__).parent.parent.parent.parent / ".pre-commit-config.yaml"
        assert precommit_file.exists(), "Missing pre-commit configuration"

        with open(precommit_file) as f:
            content = f.read()

        # Should have quality tools configured
        assert "black" in content
        assert "isort" in content
        assert "ruff" in content
        assert "mypy" in content

    def test_docker_setup_exists(self):
        """Test that Docker setup exists."""
        dockerfile = Path(__file__).parent.parent.parent.parent / "Dockerfile"
        docker_compose = Path(__file__).parent.parent.parent.parent / "docker-compose.yml"

        assert dockerfile.exists(), "Missing Dockerfile"
        assert docker_compose.exists(), "Missing docker-compose.yml"

    def test_pytest_configuration_enhanced(self):
        """Test that pytest configuration has been enhanced."""
        pyproject_toml = Path(__file__).parent.parent.parent.parent / "pyproject.toml"

        with open(pyproject_toml) as f:
            content = f.read()

        # Should have enhanced pytest configuration
        assert "[tool.pytest.ini_options]" in content
        assert "--cov=" in content  # Coverage reporting
        assert "--cov-fail-under=" in content  # Coverage threshold


class TestDocumentation:
    """Test that documentation has been created."""

    def test_refactoring_summary_exists(self):
        """Test that refactoring summary documentation exists."""
        docs_dir = Path(__file__).parent.parent.parent.parent / "docs"
        refactoring_doc = docs_dir / "REFACTORING_SUMMARY.md"

        assert refactoring_doc.exists(), "Missing refactoring summary documentation"

        with open(refactoring_doc) as f:
            content = f.read()

        assert "1,634 lines to just 84 lines" in content or "1634" in content
        assert "95%" in content  # Should mention the reduction percentage

    def test_cicd_setup_documentation_exists(self):
        """Test that CI/CD setup documentation exists."""
        docs_dir = Path(__file__).parent.parent.parent.parent / "docs"
        cicd_doc = docs_dir / "CI_CD_SETUP.md"

        assert cicd_doc.exists(), "Missing CI/CD setup documentation"

        with open(cicd_doc) as f:
            content = f.read()

        assert "CI/CD Pipeline" in content
        assert "GitHub Actions" in content
        assert "Docker" in content
