import subprocess
import sys

from conftest import TEMPLATE


def run_check(env, cwd):
    return subprocess.run(
        [sys.executable, "scripts/check_deploy.py"],
        cwd=cwd, env=env, capture_output=True, text=True,
    )


def test_correctly_configured_production_passes(installed_project, prod_env):
    """三項設定都對的正式環境，守門放行。"""
    result = run_check(prod_env, installed_project)

    assert result.returncode == 0


def test_debug_left_on_is_refused(installed_project, prod_env):
    """DEBUG 忘了關就要部署，被擋下並指名是 DEBUG。"""
    prod_env["DJANGO_DEBUG"] = "1"

    result = run_check(prod_env, installed_project)

    assert result.returncode != 0
    assert "DEBUG" in result.stdout


def test_untouched_template_secret_key_is_refused(installed_project, prod_env):
    """SECRET_KEY 還是樣板的預設值就要部署，被擋下並指名是 SECRET_KEY。"""
    prod_env["DJANGO_SECRET_KEY"] = "django-insecure-CHANGE-ME"

    result = run_check(prod_env, installed_project)

    assert result.returncode != 0
    assert "SECRET_KEY" in result.stdout


def test_wildcard_allowed_hosts_is_refused(installed_project, prod_env):
    """ALLOWED_HOSTS 放了萬用字元，被擋下並指名是 ALLOWED_HOSTS。"""
    prod_env["DJANGO_ALLOWED_HOSTS"] = "example.zeabur.app,*"

    result = run_check(prod_env, installed_project)

    assert result.returncode != 0
    assert "ALLOWED_HOSTS" in result.stdout
