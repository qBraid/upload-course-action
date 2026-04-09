# Copyright (C) 2026 qBraid

import base64
import importlib.util
import sys
from pathlib import Path
from unittest import mock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEPLOY_KERNEL_PATH = (
    PROJECT_ROOT / "deploy-kernel" / "src" / "scripts" / "deploy_kernel.py"
)


def _load_deploy_kernel_module():
    spec = importlib.util.spec_from_file_location("deploy_kernel", DEPLOY_KERNEL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(DEPLOY_KERNEL_PATH.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


deploy_kernel_module = _load_deploy_kernel_module()
FATAL_POLL_STATUS_CODES = deploy_kernel_module.FATAL_POLL_STATUS_CODES
KERNEL_ALREADY_EXISTS_CODE = deploy_kernel_module.KERNEL_ALREADY_EXISTS_CODE
MAX_POLL_ATTEMPTS = deploy_kernel_module.MAX_POLL_ATTEMPTS
POLL_INTERVAL_SECONDS = deploy_kernel_module.POLL_INTERVAL_SECONDS
REQUEST_TIMEOUT_SECONDS = deploy_kernel_module.REQUEST_TIMEOUT_SECONDS
_collect_context_files = deploy_kernel_module._collect_context_files
_encode_file = deploy_kernel_module._encode_file
_parse_error_response = deploy_kernel_module._parse_error_response
deploy_kernel = deploy_kernel_module.deploy_kernel
write_github_output = deploy_kernel_module.write_github_output


@pytest.mark.unit
class TestConstants:
    """Tests for module constants."""

    def test_max_poll_attempts(self):
        assert MAX_POLL_ATTEMPTS == 60

    def test_poll_interval(self):
        assert POLL_INTERVAL_SECONDS == 30

    def test_request_timeout(self):
        assert REQUEST_TIMEOUT_SECONDS == 30

    def test_fatal_poll_status_codes(self):
        assert FATAL_POLL_STATUS_CODES == {400, 401, 403, 404}


@pytest.mark.unit
class TestWriteGithubOutput:
    """Tests for write_github_output function."""

    def test_write_without_github_output_env(self, monkeypatch):
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        write_github_output("key", "value")

    def test_write_with_github_output_env(self, tmp_path, monkeypatch):
        output_file = tmp_path / "github_output"
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

        write_github_output("build-id", "test-build-123")
        write_github_output("kernel-name", "my_kernel")

        content = output_file.read_text()
        assert "build-id=test-build-123" in content
        assert "kernel-name=my_kernel" in content

    def test_write_multiple_outputs(self, tmp_path, monkeypatch):
        output_file = tmp_path / "github_output"
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

        write_github_output("key1", "value1")
        write_github_output("key2", "value2")

        content = output_file.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 2

    def test_write_multiline_output_uses_delimiter_format(self, tmp_path, monkeypatch):
        output_file = tmp_path / "github_output"
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

        write_github_output("error", "first line\nsecond line")

        content = output_file.read_text()
        assert "error<<" in content
        assert "first line\nsecond line" in content


@pytest.mark.unit
class TestEncodeFile:
    """Tests for _encode_file helper function."""

    def test_encode_simple_file(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("Hello, World!")

        encoded = _encode_file(file_path)
        assert isinstance(encoded, str)
        decoded = base64.b64decode(encoded)
        assert decoded == b"Hello, World!"

    def test_encode_empty_file(self, tmp_path):
        file_path = tmp_path / "empty.txt"
        file_path.write_text("")

        encoded = _encode_file(file_path)
        assert encoded == ""


@pytest.mark.unit
class TestCollectContextFiles:
    """Tests for _collect_context_files helper function."""

    def test_collect_from_empty_dir(self, tmp_path):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.touch()

        result = _collect_context_files(tmp_path, dockerfile_path)
        assert result == {}

    def test_collect_context_files_excludes_dockerfile(self, tmp_path):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text("FROM python:3.11")

        test_file = tmp_path / "requirements.txt"
        test_file.write_text("requests")

        result = _collect_context_files(tmp_path, dockerfile_path)
        assert "requirements.txt" in result
        assert "Dockerfile" not in result

    def test_collect_context_files_excludes_gitignore(self, tmp_path):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.touch()

        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc")

        result = _collect_context_files(tmp_path, dockerfile_path)
        assert ".gitignore" not in result

    def test_collect_context_files_excludes_sensitive_files(self, tmp_path):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.touch()
        (tmp_path / ".env").write_text("QBRAID_API_KEY=secret")
        (tmp_path / "secrets.pem").write_text("pem")
        (tmp_path / "requirements.txt").write_text("requests")

        result = _collect_context_files(tmp_path, dockerfile_path)

        assert ".env" not in result
        assert "secrets.pem" not in result
        assert "requirements.txt" in result

    def test_collect_context_files_skips_large_files(self, tmp_path):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.touch()

        large_file = tmp_path / "large.bin"
        large_file.write_bytes(b"x" * (11 * 1024 * 1024))

        result = _collect_context_files(tmp_path, dockerfile_path)
        assert "large.bin" not in result

    def test_collect_nested_files(self, tmp_path):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.touch()

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("content")

        result = _collect_context_files(tmp_path, dockerfile_path)
        assert "subdir/file.txt" not in result

    def test_collect_single_level_files(self, tmp_path):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.touch()

        file1 = tmp_path / "file1.txt"
        file1.write_text("content1")
        file2 = tmp_path / "file2.txt"
        file2.write_text("content2")

        result = _collect_context_files(tmp_path, dockerfile_path)
        assert "file1.txt" in result
        assert "file2.txt" in result

    def test_collect_nonexistent_dir(self):
        result = _collect_context_files(Path("/nonexistent"), Path("Dockerfile"))
        assert result == {}


@pytest.mark.unit
class TestDeployKernel:
    """Tests for deploy_kernel function."""

    def setup_method(self):
        self.valid_dockerfile = """\
FROM python:3.11-slim
LABEL qbraid.kernel.name="test_kernel" \\
      qbraid.kernel.language="python" \\
      qbraid.kernel.display_name="Test Kernel"
EXPOSE 8888
COPY kernel.json /usr/local/share/jupyter/kernels/test_kernel/
CMD ["jupyter", "kernelgateway"]
"""

    @mock.patch("deploy_kernel.time.sleep")
    @mock.patch("deploy_kernel.write_github_output")
    @mock.patch("deploy_kernel.requests.post")
    @mock.patch("deploy_kernel.requests.get")
    def test_deploy_kernel_success(
        self, mock_get, mock_post, mock_write_output, mock_sleep, tmp_path
    ):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)

        mock_post_response = mock.Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {"buildId": "build-123"}}
        mock_post.return_value = mock_post_response

        mock_get_response_active = mock.Mock()
        mock_get_response_active.status_code = 200
        mock_get_response_active.json.return_value = {
            "data": {"status": "active", "imageUri": "docker.io/image:tag"}
        }
        mock_get.return_value = mock_get_response_active

        deploy_kernel(
            api_key="test-key",
            dockerfile_path=str(dockerfile_path),
            kernel_name="test_kernel",
            language="python",
            display_name="Test Kernel",
            context_dir=str(tmp_path),
            api_base_url="https://api.qbraid.com",
        )

        mock_post.assert_called_once()
        mock_get.assert_called_once()
        mock_write_output.assert_any_call("build-id", "build-123")
        mock_write_output.assert_any_call("kernel-name", "test_kernel")
        mock_write_output.assert_any_call("status", "active")
        mock_write_output.assert_any_call("image-uri", "docker.io/image:tag")
        mock_sleep.assert_not_called()

    @mock.patch("deploy_kernel.write_github_output")
    def test_deploy_kernel_missing_dockerfile(self, mock_write_output, tmp_path):
        nonexistent_path = str(tmp_path / "nonexistent" / "Dockerfile")

        with pytest.raises(SystemExit) as exc_info:
            deploy_kernel(
                dockerfile_path=nonexistent_path,
                kernel_name="test_kernel",
                language="python",
                display_name="Test Kernel",
                context_dir=str(tmp_path),
                api_base_url="https://api.qbraid.com",
                api_key="test-key",
            )
        assert exc_info.value.code == 1

    @mock.patch("deploy_kernel.write_github_output")
    @mock.patch("deploy_kernel.requests.post")
    def test_deploy_kernel_api_error(self, mock_post, mock_write_output, tmp_path):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)

        mock_post_response = mock.Mock()
        mock_post_response.status_code = 401
        mock_post_response.text = "Unauthorized"
        mock_post.return_value = mock_post_response

        with pytest.raises(SystemExit) as exc_info:
            deploy_kernel(
                dockerfile_path=str(dockerfile_path),
                kernel_name="test_kernel",
                language="python",
                display_name="Test Kernel",
                context_dir=str(tmp_path),
                api_base_url="https://api.qbraid.com",
                api_key="bad-key",
            )
        assert exc_info.value.code == 1

    @mock.patch("deploy_kernel.write_github_output")
    @mock.patch("deploy_kernel.requests.post")
    def test_deploy_kernel_already_exists_is_treated_as_success(
        self, mock_post, mock_write_output, tmp_path
    ):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)

        mock_post_response = mock.Mock()
        mock_post_response.status_code = 400
        mock_post_response.text = "Kernel already exists"
        mock_post_response.json.return_value = {
            "success": False,
            "error": {
                "message": "Kernel 'test_kernel' already exists with status 'active'",
                "code": KERNEL_ALREADY_EXISTS_CODE,
            },
        }
        mock_post.return_value = mock_post_response

        deploy_kernel(
            dockerfile_path=str(dockerfile_path),
            kernel_name="test_kernel",
            language="python",
            display_name="Test Kernel",
            context_dir=str(tmp_path),
            api_base_url="https://api.qbraid.com",
            api_key="test-key",
        )

        mock_write_output.assert_any_call("kernel-name", "test_kernel")
        mock_write_output.assert_any_call("status", "active")

    @mock.patch("deploy_kernel.write_github_output")
    @mock.patch("deploy_kernel.requests.post")
    def test_deploy_kernel_no_build_id(self, mock_post, mock_write_output, tmp_path):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)

        mock_post_response = mock.Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {}}
        mock_post.return_value = mock_post_response

        with pytest.raises(SystemExit) as exc_info:
            deploy_kernel(
                dockerfile_path=str(dockerfile_path),
                kernel_name="test_kernel",
                language="python",
                display_name="Test Kernel",
                context_dir=str(tmp_path),
                api_base_url="https://api.qbraid.com",
                api_key="test-key",
            )
        assert exc_info.value.code == 1

    @mock.patch("deploy_kernel.time.sleep")
    @mock.patch("deploy_kernel.write_github_output")
    @mock.patch("deploy_kernel.requests.post")
    @mock.patch("deploy_kernel.requests.get")
    def test_deploy_kernel_polls_until_active(
        self, mock_get, mock_post, mock_write_output, mock_sleep, tmp_path
    ):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)

        mock_post_response = mock.Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {"buildId": "build-123"}}
        mock_post.return_value = mock_post_response

        mock_get_responses = []
        for _ in range(3):
            pending_response = mock.Mock()
            pending_response.status_code = 200
            pending_response.json.return_value = {"data": {"status": "pending"}}
            mock_get_responses.append(pending_response)

        active_response = mock.Mock()
        active_response.status_code = 200
        active_response.json.return_value = {"data": {"status": "active"}}
        mock_get_responses.append(active_response)

        mock_get.side_effect = mock_get_responses

        deploy_kernel(
            dockerfile_path=str(dockerfile_path),
            kernel_name="test_kernel",
            language="python",
            display_name="Test Kernel",
            context_dir=str(tmp_path),
            api_base_url="https://api.qbraid.com",
            api_key="test-key",
        )

        assert mock_get.call_count == 4
        mock_write_output.assert_any_call("status", "active")

    @mock.patch("deploy_kernel.time.sleep")
    @mock.patch("deploy_kernel.write_github_output")
    @mock.patch("deploy_kernel.requests.post")
    @mock.patch("deploy_kernel.requests.get")
    def test_deploy_kernel_build_failed(
        self, mock_get, mock_post, mock_write_output, mock_sleep, tmp_path
    ):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)

        mock_post_response = mock.Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {"buildId": "build-123"}}
        mock_post.return_value = mock_post_response

        failed_response = mock.Mock()
        failed_response.status_code = 200
        failed_response.json.return_value = {
            "data": {"status": "failed", "error": "Build error"}
        }
        mock_get.return_value = failed_response

        with pytest.raises(SystemExit) as exc_info:
            deploy_kernel(
                dockerfile_path=str(dockerfile_path),
                kernel_name="test_kernel",
                language="python",
                display_name="Test Kernel",
                context_dir=str(tmp_path),
                api_base_url="https://api.qbraid.com",
                api_key="test-key",
            )
        assert exc_info.value.code == 1
        mock_write_output.assert_any_call("status", "failed")

    @mock.patch("deploy_kernel.time.sleep")
    @mock.patch("deploy_kernel.write_github_output")
    @mock.patch("deploy_kernel.requests.post")
    @mock.patch("deploy_kernel.requests.get")
    def test_deploy_kernel_timeout(
        self, mock_get, mock_post, mock_write_output, mock_sleep, tmp_path
    ):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)

        mock_post_response = mock.Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {"buildId": "build-123"}}
        mock_post.return_value = mock_post_response

        pending_response = mock.Mock()
        pending_response.status_code = 200
        pending_response.json.return_value = {"data": {"status": "pending"}}
        mock_get.return_value = pending_response

        with pytest.raises(SystemExit) as exc_info:
            deploy_kernel(
                api_key="test-key",
                dockerfile_path=str(dockerfile_path),
                kernel_name="test_kernel",
                language="python",
                display_name="Test Kernel",
                context_dir=str(tmp_path),
                api_base_url="https://api.qbraid.com",
            )
        assert exc_info.value.code == 1
        mock_write_output.assert_any_call("status", "timeout")

    @mock.patch("deploy_kernel.time.sleep")
    @mock.patch("deploy_kernel.write_github_output")
    @mock.patch("deploy_kernel.requests.post")
    @mock.patch("deploy_kernel.requests.get")
    def test_deploy_kernel_with_context_files(
        self, mock_get, mock_post, mock_write_output, mock_sleep, tmp_path
    ):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)

        requirements = tmp_path / "requirements.txt"
        requirements.write_text("jupyter")

        mock_post_response = mock.Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {"buildId": "build-123"}}
        mock_post.return_value = mock_post_response

        mock_get_response = mock.Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"data": {"status": "active"}}
        mock_get.return_value = mock_get_response

        deploy_kernel(
            dockerfile_path=str(dockerfile_path),
            kernel_name="test_kernel",
            language="python",
            display_name="Test Kernel",
            context_dir=str(tmp_path),
            api_base_url="https://api.qbraid.com",
            api_key="test-key",
        )

        assert mock_post.called
        call_kwargs = mock_post.call_args
        payload = call_kwargs[1]["json"]
        assert "contextFiles" in payload
        assert "requirements.txt" in payload["contextFiles"]

    @mock.patch("deploy_kernel.write_github_output")
    @mock.patch("deploy_kernel.requests.post")
    def test_deploy_kernel_request_exception(
        self, mock_post, mock_write_output, tmp_path
    ):
        import requests

        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)

        mock_post.side_effect = requests.RequestException("Connection error")

        with pytest.raises(SystemExit) as exc_info:
            deploy_kernel(
                dockerfile_path=str(dockerfile_path),
                kernel_name="test_kernel",
                language="python",
                display_name="Test Kernel",
                context_dir=str(tmp_path),
                api_base_url="https://api.qbraid.com",
                api_key="test-key",
            )
        assert exc_info.value.code == 1

    @mock.patch("deploy_kernel.time.sleep")
    @mock.patch("deploy_kernel.write_github_output")
    @mock.patch("deploy_kernel.requests.post")
    @mock.patch("deploy_kernel.requests.get")
    def test_deploy_kernel_explicit_api_base_url(
        self, mock_get, mock_post, mock_write_output, mock_sleep, tmp_path
    ):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)

        mock_post_response = mock.Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {"buildId": "build-123"}}
        mock_post.return_value = mock_post_response

        mock_get_response = mock.Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"data": {"status": "active"}}
        mock_get.return_value = mock_get_response

        custom_url = "https://custom-api.qbraid.com/api/v1"
        deploy_kernel(
            dockerfile_path=str(dockerfile_path),
            kernel_name="test_kernel",
            language="python",
            display_name="Test Kernel",
            context_dir=str(tmp_path),
            api_base_url=custom_url,
            api_key="test-key",
        )

        post_call = mock_post.call_args
        assert custom_url in post_call[0][0]

    @mock.patch("deploy_kernel.time.sleep")
    @mock.patch("deploy_kernel.write_github_output")
    @mock.patch("deploy_kernel.requests.post")
    @mock.patch("deploy_kernel.requests.get")
    def test_deploy_kernel_poll_build_not_found_fails_fast(
        self, mock_get, mock_post, mock_write_output, mock_sleep, tmp_path
    ):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)

        mock_post_response = mock.Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {"buildId": "build-123"}}
        mock_post.return_value = mock_post_response

        missing_response = mock.Mock()
        missing_response.status_code = 404
        missing_response.text = "build missing"
        missing_response.json.return_value = {
            "success": False,
            "error": {
                "code": "BUILD_NOT_FOUND",
                "message": "Build 'build-123' not found",
            },
        }
        mock_get.return_value = missing_response

        with pytest.raises(SystemExit) as exc_info:
            deploy_kernel(
                dockerfile_path=str(dockerfile_path),
                kernel_name="test_kernel",
                language="python",
                display_name="Test Kernel",
                context_dir=str(tmp_path),
                api_base_url="https://api.qbraid.com",
                api_key="test-key",
            )

        assert exc_info.value.code == 1
        assert mock_get.call_count == 1
        mock_write_output.assert_any_call("status", "failed")

    @mock.patch("deploy_kernel.time.sleep")
    @mock.patch("deploy_kernel.write_github_output")
    @mock.patch("deploy_kernel.requests.post")
    @mock.patch("deploy_kernel.requests.get")
    def test_deploy_kernel_poll_auth_failure_fails_fast(
        self, mock_get, mock_post, mock_write_output, mock_sleep, tmp_path
    ):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)

        mock_post_response = mock.Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {"buildId": "build-123"}}
        mock_post.return_value = mock_post_response

        unauthorized_response = mock.Mock()
        unauthorized_response.status_code = 401
        unauthorized_response.text = "Unauthorized"
        unauthorized_response.json.return_value = {
            "success": False,
            "error": {"code": "UNAUTHORIZED", "message": "Invalid API key"},
        }
        mock_get.return_value = unauthorized_response

        with pytest.raises(SystemExit) as exc_info:
            deploy_kernel(
                dockerfile_path=str(dockerfile_path),
                kernel_name="test_kernel",
                language="python",
                display_name="Test Kernel",
                context_dir=str(tmp_path),
                api_base_url="https://api.qbraid.com",
                api_key="test-key",
            )

        assert exc_info.value.code == 1
        assert mock_get.call_count == 1
        mock_write_output.assert_any_call("status", "failed")

    @mock.patch("deploy_kernel.time.sleep")
    @mock.patch("deploy_kernel.write_github_output")
    @mock.patch("deploy_kernel.requests.post")
    @mock.patch("deploy_kernel.requests.get")
    def test_deploy_kernel_poll_returns_non_200_continues(
        self, mock_get, mock_post, mock_write_output, mock_sleep, tmp_path
    ):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)

        mock_post_response = mock.Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {"buildId": "build-123"}}
        mock_post.return_value = mock_post_response

        pending_response = mock.Mock()
        pending_response.status_code = 200
        pending_response.json.return_value = {"data": {"status": "pending"}}

        error_response = mock.Mock()
        error_response.status_code = 500

        def get_side_effect():
            yield pending_response
            while True:
                yield error_response

        mock_get.side_effect = get_side_effect()

        with pytest.raises(SystemExit) as exc_info:
            deploy_kernel(
                dockerfile_path=str(dockerfile_path),
                kernel_name="test_kernel",
                language="python",
                display_name="Test Kernel",
                context_dir=str(tmp_path),
                api_base_url="https://api.qbraid.com",
                api_key="test-key",
            )
        assert exc_info.value.code == 1
        mock_write_output.assert_any_call("status", "timeout")

    @mock.patch("deploy_kernel.write_github_output")
    @mock.patch("deploy_kernel.requests.post")
    def test_deploy_kernel_uses_api_key_from_env(
        self, mock_post, mock_write_output, tmp_path, monkeypatch
    ):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)
        monkeypatch.setenv("QBRAID_API_KEY", "env-api-key")

        mock_post_response = mock.Mock()
        mock_post_response.status_code = 400
        mock_post_response.text = "Kernel already exists"
        mock_post_response.json.return_value = {
            "error": {
                "message": "Kernel 'test_kernel' already exists",
                "code": KERNEL_ALREADY_EXISTS_CODE,
            }
        }
        mock_post.return_value = mock_post_response

        deploy_kernel(
            dockerfile_path=str(dockerfile_path),
            kernel_name="test_kernel",
            language="python",
            display_name="Test Kernel",
            context_dir=str(tmp_path),
            api_base_url="https://api.qbraid.com",
        )

        headers = mock_post.call_args.kwargs["headers"]
        assert headers["X-API-Key"] == "env-api-key"

    def test_deploy_kernel_rejects_invalid_kernel_name(self, tmp_path):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(self.valid_dockerfile)

        with pytest.raises(SystemExit) as exc_info:
            deploy_kernel(
                dockerfile_path=str(dockerfile_path),
                kernel_name="Invalid-Name",
                language="python",
                display_name="Test Kernel",
                context_dir=str(tmp_path),
                api_base_url="https://api.qbraid.com",
                api_key="test-key",
            )

        assert exc_info.value.code == 1

    def test_deploy_kernel_rejects_label_mismatch(self, tmp_path):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(
            self.valid_dockerfile.replace('qbraid.kernel.name="test_kernel"', 'qbraid.kernel.name="other_kernel"')
        )

        with pytest.raises(SystemExit) as exc_info:
            deploy_kernel(
                dockerfile_path=str(dockerfile_path),
                kernel_name="test_kernel",
                language="python",
                display_name="Test Kernel",
                context_dir=str(tmp_path),
                api_base_url="https://api.qbraid.com",
                api_key="test-key",
            )

        assert exc_info.value.code == 1


@pytest.mark.unit
class TestParseErrorResponse:
    def test_prefers_structured_error_payload(self):
        response = mock.Mock()
        response.text = "fallback"
        response.json.return_value = {
            "error": {"code": KERNEL_ALREADY_EXISTS_CODE, "message": "already there"}
        }

        error_code, message = _parse_error_response(response)

        assert error_code == KERNEL_ALREADY_EXISTS_CODE
        assert message == "already there"

    def test_falls_back_to_response_text_for_non_json(self):
        response = mock.Mock()
        response.text = "plain text error"
        response.json.side_effect = ValueError("invalid json")

        error_code, message = _parse_error_response(response)

        assert error_code is None
        assert message == "plain text error"
