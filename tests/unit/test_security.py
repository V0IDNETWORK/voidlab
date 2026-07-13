"""Unit tests for security utilities."""

from __future__ import annotations

import pytest

from voidremote.utils.security import (
    is_safe_filename,
    sanitize_shell_arg,
    sanitize_shell_args,
    validate_device_path,
    validate_host,
    validate_ip_address,
    validate_package_name,
    validate_pairing_code,
    validate_port,
)


class TestValidateIpAddress:
    def test_valid_ipv4(self) -> None:
        assert validate_ip_address("192.168.1.1") == "192.168.1.1"

    def test_valid_ipv6(self) -> None:
        assert validate_ip_address("::1") == "::1"

    def test_invalid(self) -> None:
        with pytest.raises(ValueError):
            validate_ip_address("not_an_ip")

    def test_empty(self) -> None:
        with pytest.raises(ValueError):
            validate_ip_address("")


class TestValidateHost:
    def test_valid_ip(self) -> None:
        assert validate_host("192.168.1.50") == "192.168.1.50"

    def test_valid_hostname(self) -> None:
        assert validate_host("my-android.local") == "my-android.local"

    def test_strips_whitespace(self) -> None:
        assert validate_host("  192.168.1.1  ") == "192.168.1.1"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            validate_host("")

    def test_too_long(self) -> None:
        with pytest.raises(ValueError):
            validate_host("a" * 300)


class TestValidatePort:
    def test_valid_int(self) -> None:
        assert validate_port(5555) == 5555

    def test_valid_string(self) -> None:
        assert validate_port("8080") == 8080

    def test_min_port(self) -> None:
        assert validate_port(1) == 1

    def test_max_port(self) -> None:
        assert validate_port(65535) == 65535

    def test_zero_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_port(0)

    def test_too_high(self) -> None:
        with pytest.raises(ValueError):
            validate_port(65536)

    def test_non_numeric(self) -> None:
        with pytest.raises(ValueError):
            validate_port("abc")


class TestValidatePairingCode:
    def test_valid_6_digit(self) -> None:
        assert validate_pairing_code("123456") == "123456"

    def test_strips_whitespace(self) -> None:
        assert validate_pairing_code("  654321  ") == "654321"

    def test_too_short(self) -> None:
        with pytest.raises(ValueError):
            validate_pairing_code("12345")

    def test_too_long(self) -> None:
        with pytest.raises(ValueError):
            validate_pairing_code("1234567")

    def test_non_digit(self) -> None:
        with pytest.raises(ValueError):
            validate_pairing_code("12345a")

    def test_empty(self) -> None:
        with pytest.raises(ValueError):
            validate_pairing_code("")


class TestSanitizeShellArg:
    def test_safe_arg(self) -> None:
        assert "hello" in sanitize_shell_arg("hello")

    def test_semicolon_raises(self) -> None:
        with pytest.raises(ValueError):
            sanitize_shell_arg("hello; rm -rf /")

    def test_pipe_raises(self) -> None:
        with pytest.raises(ValueError):
            sanitize_shell_arg("hello | cat /etc/passwd")

    def test_backtick_raises(self) -> None:
        with pytest.raises(ValueError):
            sanitize_shell_arg("`id`")

    def test_dollar_raises(self) -> None:
        with pytest.raises(ValueError):
            sanitize_shell_arg("$(id)")

    def test_list(self) -> None:
        assert len(sanitize_shell_args(["ls", "-la"])) == 2

    def test_list_with_injection(self) -> None:
        with pytest.raises(ValueError):
            sanitize_shell_args(["ls", "; rm -rf /"])


class TestValidatePackageName:
    def test_valid_package(self) -> None:
        assert validate_package_name("com.example.app") == "com.example.app"

    def test_valid_with_underscores(self) -> None:
        assert validate_package_name("com.example.my_app") == "com.example.my_app"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_package_name("")

    def test_starts_with_digit_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_package_name("1com.example")

    def test_with_spaces_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_package_name("com.example app")


class TestValidateDevicePath:
    def test_valid_absolute(self) -> None:
        assert validate_device_path("/sdcard/file.txt") == "/sdcard/file.txt"

    def test_relative_raises(self) -> None:
        with pytest.raises(ValueError, match="absolute"):
            validate_device_path("sdcard/file.txt")

    def test_null_byte_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_device_path("/sdcard/\x00evil")

    def test_parent_traversal_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_device_path("/sdcard/../etc/passwd")


class TestIsSafeFilename:
    def test_safe(self) -> None:
        assert is_safe_filename("my_file.txt") is True
        assert is_safe_filename("backup 2024.zip") is True

    def test_parent_traversal(self) -> None:
        assert is_safe_filename("../evil") is False

    def test_shell_chars(self) -> None:
        assert is_safe_filename("file;rm") is False
