"""Tests for systemd check injection."""

from generate_container_packages.systemd_check import (
    SYSTEMD_CHECK_VALUE,
    inject_systemd_check,
)


class TestInjectSystemdCheck:
    """Tests for inject_systemd_check function."""

    def test_adds_check_to_empty_service(self) -> None:
        """Check is added to service without environment."""
        compose = {"services": {"app": {}}}
        result = inject_systemd_check(compose)

        env = result["services"]["app"]["environment"]
        assert any("_HALOS_SYSTEMD_CHECK=" in e for e in env)

    def test_adds_check_to_list_environment(self) -> None:
        """Check is added to existing list-format environment."""
        compose = {"services": {"app": {"environment": ["FOO=bar", "BAZ=qux"]}}}
        result = inject_systemd_check(compose)

        env = result["services"]["app"]["environment"]
        assert "FOO=bar" in env
        assert "BAZ=qux" in env
        assert any("_HALOS_SYSTEMD_CHECK=" in e for e in env)

    def test_adds_check_to_dict_environment(self) -> None:
        """Check is added to existing dict-format environment."""
        compose = {"services": {"app": {"environment": {"FOO": "bar", "BAZ": "qux"}}}}
        result = inject_systemd_check(compose)

        env = result["services"]["app"]["environment"]
        assert env["FOO"] == "bar"
        assert env["BAZ"] == "qux"
        assert "_HALOS_SYSTEMD_CHECK" in env
        assert env["_HALOS_SYSTEMD_CHECK"] == SYSTEMD_CHECK_VALUE

    def test_check_contains_required_variable_syntax(self) -> None:
        """Check uses bash required variable syntax."""
        compose = {"services": {"app": {}}}
        result = inject_systemd_check(compose)

        env = result["services"]["app"]["environment"]
        check_entry = next(e for e in env if "_HALOS_SYSTEMD_CHECK=" in e)
        # Should contain ${VAR:?error} syntax
        assert "${HALOS_SYSTEMD_STARTED:?" in check_entry
        assert "systemctl" in check_entry.lower()

    def test_only_adds_to_first_service(self) -> None:
        """Check is only added to the first service."""
        compose = {
            "services": {
                "app": {},
                "db": {},
                "cache": {},
            }
        }
        result = inject_systemd_check(compose)

        # First service should have check
        first_env = result["services"]["app"].get("environment", [])
        assert any("_HALOS_SYSTEMD_CHECK" in str(e) for e in first_env)

        # Other services should not
        db_env = result["services"]["db"].get("environment", [])
        assert not any("_HALOS_SYSTEMD_CHECK" in str(e) for e in db_env)

        cache_env = result["services"]["cache"].get("environment", [])
        assert not any("_HALOS_SYSTEMD_CHECK" in str(e) for e in cache_env)

    def test_does_not_duplicate_check(self) -> None:
        """Check is not duplicated if already present."""
        compose = {
            "services": {
                "app": {"environment": [f"_HALOS_SYSTEMD_CHECK={SYSTEMD_CHECK_VALUE}"]}
            }
        }
        result = inject_systemd_check(compose)

        env = result["services"]["app"]["environment"]
        check_count = sum(1 for e in env if "_HALOS_SYSTEMD_CHECK=" in e)
        assert check_count == 1

    def test_does_not_duplicate_check_dict_format(self) -> None:
        """Check is not duplicated if already present in dict format."""
        compose = {
            "services": {
                "app": {"environment": {"_HALOS_SYSTEMD_CHECK": SYSTEMD_CHECK_VALUE}}
            }
        }
        result = inject_systemd_check(compose)

        env = result["services"]["app"]["environment"]
        assert "_HALOS_SYSTEMD_CHECK" in env
        assert len(env) == 1

    def test_does_not_modify_original(self) -> None:
        """Original compose dict is not modified."""
        compose = {"services": {"app": {"environment": ["FOO=bar"]}}}
        result = inject_systemd_check(compose)

        # Original should be unchanged
        assert len(compose["services"]["app"]["environment"]) == 1
        # Result should have the check added
        assert len(result["services"]["app"]["environment"]) == 2

    def test_empty_services_returns_unchanged(self) -> None:
        """Compose with empty services returns unchanged."""
        compose = {"services": {}}
        result = inject_systemd_check(compose)
        assert result == {"services": {}}

    def test_no_services_returns_unchanged(self) -> None:
        """Compose without services key returns unchanged."""
        compose = {"version": "3"}
        result = inject_systemd_check(compose)
        assert result == {"version": "3"}
