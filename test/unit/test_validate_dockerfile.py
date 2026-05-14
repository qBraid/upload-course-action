# Copyright (C) 2026 qBraid

import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_PATH = PROJECT_ROOT / "src" / "scripts"
vd_spec = importlib.util.spec_from_file_location(
    "validate_dockerfile", SCRIPTS_PATH / "validate_dockerfile.py"
)
vd_module = importlib.util.module_from_spec(vd_spec)
vd_spec.loader.exec_module(vd_module)

DockerfileValidationResult = vd_module.DockerfileValidationResult
KERNEL_NAME_PATTERN = vd_module.KERNEL_NAME_PATTERN
SUPPORTED_LANGUAGES = vd_module.SUPPORTED_LANGUAGES
_check_copy_add_sources = vd_module._check_copy_add_sources
_parse_copy_add_sources = vd_module._parse_copy_add_sources
_get_cmd_or_entrypoint = vd_module._get_cmd_or_entrypoint
_get_final_user = vd_module._get_final_user
_has_expose_8888 = vd_module._has_expose_8888
_has_kernel_json_copy = vd_module._has_kernel_json_copy
_has_privileged_flags = vd_module._has_privileged_flags
_join_continuation_lines = vd_module._join_continuation_lines
_parse_labels = vd_module._parse_labels
validate_dockerfile = vd_module.validate_dockerfile
validate_dockerfile_file = vd_module.validate_dockerfile_file
extract_dockerfile_labels = vd_module.extract_dockerfile_labels


VALID_DOCKERFILE = """\
FROM python:3.11-slim

LABEL qbraid.kernel.name="my_python_kernel" \\
      qbraid.kernel.language="python" \\
      qbraid.kernel.display_name="My Python Kernel"

WORKDIR /app

COPY kernel.json /usr/local/share/jupyter/kernels/my_python_kernel/kernel.json

EXPOSE 8888

CMD ["jupyter", "kernelgateway", "--KernelGatewayApp.ip=0.0.0.0", "--KernelGatewayApp.port=8888"]
"""


@pytest.mark.unit
class TestDockerfileValidationResult:
    """Tests for DockerfileValidationResult dataclass."""

    def test_empty_result_is_valid(self):
        result = DockerfileValidationResult()
        assert result.is_valid is True
        assert result.errors == []

    def test_add_error_makes_invalid(self):
        result = DockerfileValidationResult()
        result.add_error("Test error")
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0] == "Test error"

    def test_multiple_errors(self):
        result = DockerfileValidationResult()
        result.add_error("Error 1")
        result.add_error("Error 2")
        assert result.is_valid is False
        assert len(result.errors) == 2


@pytest.mark.unit
class TestParseLabels:
    """Tests for _parse_labels helper function."""

    def test_parse_single_label(self):
        lines = ['LABEL key="value"']
        labels = _parse_labels(lines)
        assert labels == {"key": "value"}

    def test_parse_multiple_labels_same_line(self):
        lines = ['LABEL key1="value1" key2="value2"']
        labels = _parse_labels(lines)
        assert labels == {"key1": "value1", "key2": "value2"}

    def test_parse_labels_with_backslash_continuation(self):
        lines = ['LABEL key1="value1" \\', '      key2="value2"']
        labels = _parse_labels(lines)
        assert labels.get("key1") == "value1"

    def test_parse_label_without_quotes(self):
        lines = ["LABEL key=value"]
        labels = _parse_labels(lines)
        assert labels == {"key": "value"}

    def test_ignore_non_label_lines(self):
        lines = ["FROM python:3.11", "LABEL key=value", "RUN echo hello"]
        labels = _parse_labels(lines)
        assert labels == {"key": "value"}

    def test_extract_dockerfile_labels_from_content(self):
        labels = extract_dockerfile_labels(VALID_DOCKERFILE)
        assert labels["qbraid.kernel.name"] == "my_python_kernel"


@pytest.mark.unit
class TestJoinContinuationLines:
    """Tests for _join_continuation_lines helper function."""

    def test_join_simple_lines(self):
        raw_lines = ["line1", "line2", "line3"]
        result = _join_continuation_lines(raw_lines)
        assert result == ["line1", "line2", "line3"]

    def test_join_continuation_lines(self):
        raw_lines = ["line1 \\", "line2 \\", "line3"]
        result = _join_continuation_lines(raw_lines)
        assert result == ["line1  line2  line3"]

    def test_skip_comments(self):
        raw_lines = ["# comment", "line1", "# another comment", "line2"]
        result = _join_continuation_lines(raw_lines)
        assert result == ["line1", "line2"]

    def test_handle_empty_content(self):
        raw_lines = ["", "   ", ""]
        result = _join_continuation_lines(raw_lines)
        assert result == []

    def test_trailing_backslash_with_no_next_line(self):
        raw_lines = ["line1 \\", "line2"]
        result = _join_continuation_lines(raw_lines)
        assert result == ["line1  line2"]


@pytest.mark.unit
class TestGetFinalUser:
    """Tests for _get_final_user helper function."""

    def test_get_user_directive(self):
        lines = ["FROM python:3.11", "USER root", "USER nobody"]
        assert _get_final_user(lines) == "nobody"

    def test_no_user_directive(self):
        lines = ["FROM python:3.11", "RUN pip install something"]
        assert _get_final_user(lines) is None

    def test_user_case_insensitive(self):
        lines = ["user ubuntu"]
        assert _get_final_user(lines) == "ubuntu"


@pytest.mark.unit
class TestHasExpose8888:
    """Tests for _has_expose_8888 helper function."""

    def test_expose_8888(self):
        lines = ["EXPOSE 8888"]
        assert _has_expose_8888(lines) is True

    def test_expose_8888_with_other_ports(self):
        lines = ["EXPOSE 8080 8888 3000"]
        assert _has_expose_8888(lines) is True

    def test_expose_8888_tcp(self):
        lines = ["EXPOSE 8888/tcp"]
        assert _has_expose_8888(lines) is True

    def test_no_expose_8888(self):
        lines = ["EXPOSE 8080", "EXPOSE 3000"]
        assert _has_expose_8888(lines) is False

    def test_case_insensitive(self):
        lines = ["expose 8888"]
        assert _has_expose_8888(lines) is True


@pytest.mark.unit
class TestGetCmdOrEntrypoint:
    """Tests for _get_cmd_or_entrypoint helper function."""

    def test_get_cmd(self):
        lines = ['CMD ["jupyter", "kernelgateway"]']
        assert _get_cmd_or_entrypoint(lines) is not None
        assert "kernelgateway" in _get_cmd_or_entrypoint(lines).lower()

    def test_get_entrypoint(self):
        lines = ['ENTRYPOINT ["jupyter", "kernelgateway"]']
        assert _get_cmd_or_entrypoint(lines) is not None

    def test_prefers_last_cmd(self):
        lines = ['CMD ["echo", "first"]', 'CMD ["jupyter", "kernelgateway"]']
        result = _get_cmd_or_entrypoint(lines)
        assert "kernelgateway" in result.lower()

    def test_no_cmd_or_entrypoint(self):
        lines = ["FROM python:3.11", "RUN pip install something"]
        assert _get_cmd_or_entrypoint(lines) is None


@pytest.mark.unit
class TestHasKernelJsonCopy:
    """Tests for _has_kernel_json_copy helper function."""

    def test_copy_kernel_json(self):
        lines = ["COPY kernel.json /usr/local/share/jupyter/kernels/"]
        assert _has_kernel_json_copy(lines) is True

    def test_add_kernel_json(self):
        lines = ["ADD kernel.json /usr/local/share/jupyter/kernels/"]
        assert _has_kernel_json_copy(lines) is True

    def test_run_echo_kernel_json(self):
        lines = ['RUN echo \'{"kernel": "spec"}\' > kernel.json']
        assert _has_kernel_json_copy(lines) is True

    def test_run_cat_kernel_json(self):
        lines = ["RUN cat > kernel.json << EOF"]
        assert _has_kernel_json_copy(lines) is True

    def test_run_kernelspec(self):
        lines = ["RUN jupyter kernelspec install-self --kernel=kernel.json"]
        assert _has_kernel_json_copy(lines) is True

    def test_run_ipykernel_install(self):
        lines = [
            "RUN python -m ipykernel install --name my_python_kernel --prefix /usr/local"
        ]
        assert _has_kernel_json_copy(lines) is True

    def test_no_kernel_json(self):
        lines = ["COPY requirements.txt /app/", "RUN pip install -r requirements.txt"]
        assert _has_kernel_json_copy(lines) is False


@pytest.mark.unit
class TestHasPrivilegedFlags:
    """Tests for _has_privileged_flags helper function."""

    def test_privileged_flag(self):
        lines = ["docker run --privileged"]
        assert _has_privileged_flags(lines) is True

    def test_cap_add_sys_admin(self):
        lines = ["docker run --cap-add=SYS_ADMIN"]
        assert _has_privileged_flags(lines) is True

    def test_no_privileged_flags(self):
        lines = ["docker run -p 8888:8888", "docker build -t myimage ."]
        assert _has_privileged_flags(lines) is False


@pytest.mark.unit
class TestKernelNamePattern:
    """Tests for KERNEL_NAME_PATTERN regex."""

    def test_valid_kernel_names(self):
        valid_names = ["python", "my_kernel", "python_3", "abc", "a123bc"]
        for name in valid_names:
            assert KERNEL_NAME_PATTERN.match(name), f"Expected {name} to be valid"

    def test_invalid_kernel_names(self):
        invalid_names = ["", "ab", "Python", "_python", "-python", "has space"]
        for name in invalid_names:
            assert not KERNEL_NAME_PATTERN.match(name), f"Expected {name} to be invalid"

    def test_kernel_name_too_long(self):
        long_name = "a" + "b" * 64
        assert not KERNEL_NAME_PATTERN.match(long_name)


@pytest.mark.unit
class TestSupportedLanguages:
    """Tests for SUPPORTED_LANGUAGES constant."""

    def test_expected_languages(self):
        expected = {"python", "cpp", "julia", "r", "rust", "go", "javascript"}
        assert SUPPORTED_LANGUAGES == expected


@pytest.mark.unit
class TestValidateDockerfile:
    """Tests for validate_dockerfile function."""

    def test_valid_dockerfile(self):
        result = validate_dockerfile(VALID_DOCKERFILE)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_empty_dockerfile(self):
        result = validate_dockerfile("")
        assert result.is_valid is False
        assert "Dockerfile is empty" in result.errors

    def test_dockerfile_only_comments(self):
        result = validate_dockerfile("# Comment only\n# Another comment")
        assert result.is_valid is False
        assert "no instructions" in result.errors[0]

    def test_missing_required_labels(self):
        dockerfile = """\
FROM python:3.11-slim
EXPOSE 8888
CMD ["jupyter", "kernelgateway"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is False
        assert any("Missing required LABEL" in e for e in result.errors)

    def test_invalid_kernel_name_format(self):
        dockerfile = """\
FROM python:3.11-slim
LABEL qbraid.kernel.name="Invalid-Name" \\
      qbraid.kernel.language="python" \\
      qbraid.kernel.display_name="Test"
EXPOSE 8888
COPY kernel.json /kernels/
CMD ["jupyter", "kernelgateway"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is False
        assert any(
            "qbraid.kernel.name" in e and "invalid" in e.lower() for e in result.errors
        )

    def test_unsupported_language(self):
        dockerfile = """\
FROM golang:1.21
LABEL qbraid.kernel.name="my_go_kernel" \\
      qbraid.kernel.language="cobol" \\
      qbraid.kernel.display_name="COBOL Kernel"
EXPOSE 8888
COPY kernel.json /kernels/
CMD ["jupyter", "kernelgateway"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is False
        assert any(
            "language" in e.lower() and "not supported" in e.lower()
            for e in result.errors
        )

    def test_empty_display_name(self):
        dockerfile = """\
FROM python:3.11-slim
LABEL qbraid.kernel.name="my_kernel" \\
      qbraid.kernel.language="python" \\
      qbraid.kernel.display_name=""
EXPOSE 8888
COPY kernel.json /kernels/
CMD ["jupyter", "kernelgateway"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is False
        assert any(
            "display_name" in e.lower() and "empty" in e.lower() for e in result.errors
        )

    def test_missing_expose_8888(self):
        dockerfile = """\
FROM python:3.11-slim
LABEL qbraid.kernel.name="my_kernel" \\
      qbraid.kernel.language="python" \\
      qbraid.kernel.display_name="My Kernel"
COPY kernel.json /kernels/
CMD ["jupyter", "kernelgateway"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is False
        assert any("EXPOSE 8888" in e for e in result.errors)

    def test_missing_cmd(self):
        dockerfile = """\
FROM python:3.11-slim
LABEL qbraid.kernel.name="my_kernel" \\
      qbraid.kernel.language="python" \\
      qbraid.kernel.display_name="My Kernel"
EXPOSE 8888
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is False
        assert any("CMD or ENTRYPOINT" in e for e in result.errors)

    def test_cmd_without_kernelgateway(self):
        dockerfile = """\
FROM python:3.11-slim
LABEL qbraid.kernel.name="my_kernel" \\
      qbraid.kernel.language="python" \\
      qbraid.kernel.display_name="My Kernel"
EXPOSE 8888
CMD ["python", "-m", "http.server"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is False
        assert any("kernelgateway" in e.lower() for e in result.errors)

    def test_root_user(self):
        dockerfile = """\
FROM python:3.11-slim
LABEL qbraid.kernel.name="my_kernel" \\
      qbraid.kernel.language="python" \\
      qbraid.kernel.display_name="My Kernel"
USER root
EXPOSE 8888
COPY kernel.json /kernels/
CMD ["jupyter", "kernelgateway"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is False
        assert any("root" in e.lower() for e in result.errors)

    def test_privileged_flag(self):
        dockerfile = """\
FROM python:3.11-slim
LABEL qbraid.kernel.name="my_kernel" \\
      qbraid.kernel.language="python" \\
      qbraid.kernel.display_name="My Kernel"
EXPOSE 8888
COPY kernel.json /kernels/
CMD ["jupyter", "kernelgateway", "--KernelGatewayApp.prespawned_env=foo=--privileged"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is False
        assert any("privileged" in e.lower() for e in result.errors)

    def test_missing_kernel_json(self):
        dockerfile = """\
FROM python:3.11-slim
LABEL qbraid.kernel.name="my_kernel" \\
      qbraid.kernel.language="python" \\
      qbraid.kernel.display_name="My Kernel"
EXPOSE 8888
CMD ["jupyter", "kernelgateway"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is False
        assert any("kernel.json" in e for e in result.errors)

    def test_valid_cpp_dockerfile(self):
        dockerfile = """\
FROM gcc:latest
LABEL qbraid.kernel.name="my_cpp_kernel" \\
      qbraid.kernel.language="cpp" \\
      qbraid.kernel.display_name="C++ Kernel"
EXPOSE 8888
COPY kernel.json /usr/local/share/jupyter/kernels/my_cpp_kernel/
CMD ["jupyter", "kernelgateway"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is True

    def test_valid_julia_dockerfile(self):
        dockerfile = """\
FROM julia:latest
LABEL qbraid.kernel.name="my_julia_kernel" \\
      qbraid.kernel.language="julia" \\
      qbraid.kernel.display_name="Julia Kernel"
EXPOSE 8888
COPY kernel.json /usr/local/share/jupyter/kernels/my_julia_kernel/
CMD ["jupyter", "kernelgateway"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is True

    def test_valid_rust_dockerfile(self):
        dockerfile = """\
FROM rust:latest
LABEL qbraid.kernel.name="my_rust_kernel" \\
      qbraid.kernel.language="rust" \\
      qbraid.kernel.display_name="Rust Kernel"
EXPOSE 8888
COPY kernel.json /usr/local/share/jupyter/kernels/my_rust_kernel/
CMD ["jupyter", "kernelgateway"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is True

    def test_valid_go_dockerfile(self):
        dockerfile = """\
FROM golang:latest
LABEL qbraid.kernel.name="my_go_kernel" \\
      qbraid.kernel.language="go" \\
      qbraid.kernel.display_name="Go Kernel"
EXPOSE 8888
COPY kernel.json /usr/local/share/jupyter/kernels/my_go_kernel/
CMD ["jupyter", "kernelgateway"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is True

    def test_valid_javascript_dockerfile(self):
        dockerfile = """\
FROM node:latest
LABEL qbraid.kernel.name="my_js_kernel" \\
      qbraid.kernel.language="javascript" \\
      qbraid.kernel.display_name="JavaScript Kernel"
EXPOSE 8888
COPY kernel.json /usr/local/share/jupyter/kernels/my_js_kernel/
CMD ["jupyter", "kernelgateway"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is True

    def test_valid_r_dockerfile(self):
        dockerfile = """\
FROM r-base:latest
LABEL qbraid.kernel.name="my_r_kernel" \\
      qbraid.kernel.language="r" \\
      qbraid.kernel.display_name="R Kernel"
EXPOSE 8888
COPY kernel.json /usr/local/share/jupyter/kernels/my_r_kernel/
CMD ["jupyter", "kernelgateway"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is True

    def test_entrypoint_instead_of_cmd(self):
        dockerfile = """\
FROM python:3.11-slim
LABEL qbraid.kernel.name="my_kernel" \\
      qbraid.kernel.language="python" \\
      qbraid.kernel.display_name="My Kernel"
EXPOSE 8888
COPY kernel.json /kernels/
ENTRYPOINT ["jupyter", "kernelgateway"]
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is True

    def test_kernel_gateway_underscore_variant(self):
        dockerfile = """\
FROM python:3.11-slim
LABEL qbraid.kernel.name="my_kernel" \\
      qbraid.kernel.language="python" \\
      qbraid.kernel.display_name="My Kernel"
EXPOSE 8888
COPY kernel.json /kernels/
CMD jupyter kernel_gateway
"""
        result = validate_dockerfile(dockerfile)
        assert result.is_valid is True


@pytest.mark.unit
class TestValidateDockerfileFile:
    """Tests for validate_dockerfile_file function."""

    def test_validate_existing_file(self, tmp_path):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text(VALID_DOCKERFILE)

        try:
            validate_dockerfile_file(str(dockerfile_path))
        except SystemExit:
            pytest.fail("validate_dockerfile_file exited unexpectedly for valid file")

    def test_validate_nonexistent_file(self):
        with pytest.raises(SystemExit) as exc_info:
            validate_dockerfile_file("/nonexistent/path/Dockerfile")
        assert exc_info.value.code == 1

    def test_validate_invalid_file(self, tmp_path):
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text("FROM python:3.11")

        with pytest.raises(SystemExit) as exc_info:
            validate_dockerfile_file(str(dockerfile_path))
        assert exc_info.value.code == 1


VALID_BASE = """\
FROM python:3.11-slim
LABEL qbraid.kernel.name="my_kernel" qbraid.kernel.language="python" qbraid.kernel.display_name="My Kernel"
COPY kernel.json /usr/local/share/jupyter/kernels/my_kernel/kernel.json
EXPOSE 8888
USER 1000
CMD ["jupyter", "kernelgateway"]
"""


@pytest.mark.unit
class TestParseCopyAddSources:
    """Tokenize COPY/ADD source paths."""

    def test_simple_copy(self):
        assert _parse_copy_add_sources("COPY a.txt /dst/") == ["a.txt"]

    def test_multiple_sources(self):
        assert _parse_copy_add_sources("COPY a.txt b.txt /dst/") == [
            "a.txt",
            "b.txt",
        ]

    def test_add_directive(self):
        assert _parse_copy_add_sources("ADD foo.tar.gz /opt/") == ["foo.tar.gz"]

    def test_non_copy_returns_none(self):
        assert _parse_copy_add_sources("RUN echo hi") is None

    def test_multi_stage_from_skipped(self):
        assert _parse_copy_add_sources("COPY --from=builder /out /dst/") is None

    def test_chown_chmod_flags_stripped(self):
        assert _parse_copy_add_sources("COPY --chown=1000:1000 a.txt /dst/") == [
            "a.txt"
        ]
        assert _parse_copy_add_sources("COPY --chmod=755 a.txt /dst/") == ["a.txt"]

    def test_json_array_form(self):
        assert _parse_copy_add_sources('COPY ["a.txt", "b.txt", "/dst/"]') == [
            "a.txt",
            "b.txt",
        ]

    def test_too_few_args(self):
        assert _parse_copy_add_sources("COPY a.txt") is None


@pytest.mark.unit
class TestCheckCopyAddSources:
    """Verify COPY/ADD sources exist in the packaged build context."""

    def test_present_source_passes(self):
        assert _check_copy_add_sources(["COPY a.txt /dst/"], {"a.txt"}) == []

    def test_missing_source_fails(self):
        errors = _check_copy_add_sources(["COPY a.txt /dst/"], set())
        assert len(errors) == 1
        assert "a.txt" in errors[0]

    def test_url_source_skipped(self):
        errors = _check_copy_add_sources(
            ["ADD https://example.com/x.tar /opt/"], set()
        )
        assert errors == []

    def test_var_interpolation_warns_not_fails(self):
        # `$VAR` references can't be resolved statically; we don't fail on them.
        assert _check_copy_add_sources(["COPY ${VAR}/file /dst/"], set()) == []

    def test_dotslash_prefix_normalized(self):
        assert _check_copy_add_sources(["COPY ./a.txt /dst/"], {"a.txt"}) == []

    def test_subdir_top_level_check(self):
        # `COPY src/main.py …` should pass when `src` is in the packaged set.
        assert _check_copy_add_sources(["COPY src/main.py /dst/"], {"src"}) == []
        errors = _check_copy_add_sources(["COPY src/main.py /dst/"], set())
        assert len(errors) == 1


@pytest.mark.unit
class TestValidateDockerfileWithContext:
    """Integration: validate_dockerfile gates on the context_files set."""

    def test_no_context_files_skips_check(self):
        # Backwards-compat: if the caller didn't compute a packaged set,
        # the COPY/ADD presence check doesn't run.
        content = VALID_BASE + "COPY pyproject.toml /app/\n"
        result = validate_dockerfile(content, context_files=None)
        assert result.is_valid

    def test_missing_context_file_reported(self):
        content = VALID_BASE + "COPY pyproject.toml /app/\n"
        result = validate_dockerfile(content, context_files={"kernel.json"})
        assert not result.is_valid
        assert any("pyproject.toml" in e for e in result.errors)

    def test_present_context_file_passes(self):
        content = VALID_BASE + "COPY pyproject.toml /app/\n"
        result = validate_dockerfile(
            content, context_files={"kernel.json", "pyproject.toml"}
        )
        assert result.is_valid

    def test_bloqade_repro(self):
        """The exact failure that wedged the bloqade build (2026-05-14)."""
        content = VALID_BASE + "COPY pyproject.toml uv.lock ./\n"
        result = validate_dockerfile(content, context_files={"kernel.json"})
        assert not result.is_valid
        assert any("pyproject.toml" in e for e in result.errors)
        assert any("uv.lock" in e for e in result.errors)
