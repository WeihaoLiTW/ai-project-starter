import subprocess
import sys


def run_check(env, cwd):
    return subprocess.run(
        [sys.executable, "scripts/check_deploy.py"],
        cwd=cwd, env=env, capture_output=True, text=True,
    )


def run_django_deploy_check(env, cwd):
    return subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=cwd, env=env, capture_output=True, text=True,
    )


def test_correctly_configured_production_passes(installed_project, prod_env):
    """三項設定都對的正式環境，守門放行。"""
    result = run_check(prod_env, installed_project)

    assert result.returncode == 0


def test_djangos_own_deploy_check_passes_with_correct_settings(installed_project, prod_env):
    """CI 的 deploy-safety job 實際跑的指令（`manage.py check --deploy
    --fail-level WARNING`），設定都正確時要過。之前 SECURE_HSTS_SECONDS
    跟 SECURE_SSL_REDIRECT 沒設，即使四個環境變數都填對，這一項還是紅的，
    而且永遠不會轉綠——這個測試釘住「設定對了就是綠的」。"""
    result = run_django_deploy_check(prod_env, installed_project)

    assert result.returncode == 0, result.stdout + result.stderr


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


def test_empty_secret_key_is_refused_cleanly_not_with_a_traceback(installed_project, prod_env):
    """SECRET_KEY 完全沒設（空字串）的時候，Django 自己的 LazySettings 對這個
    設定會丟 ImproperlyConfigured，不是一般的 AttributeError——`getattr` 的
    預設值救不了這種情況。這個守門腳本在每次部署都會跑，讀不懂 stack trace
    的人看到的必須是「SECRET_KEY 是空的」這種話，不是一段 Python 例外訊息。"""
    prod_env["DJANGO_SECRET_KEY"] = ""

    result = run_check(prod_env, installed_project)

    assert result.returncode != 0
    assert "SECRET_KEY" in result.stdout
    assert "Traceback" not in result.stdout
    assert "ImproperlyConfigured" not in result.stdout + result.stderr
