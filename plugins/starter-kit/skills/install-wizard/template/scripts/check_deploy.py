"""Refuse to deploy a production configuration that is unsafe.

Django's own deploy check covers DEBUG and the insecure default key, but it
only flags an ALLOWED_HOSTS that is empty. A wildcard passes its check and
fails ours.
"""

import os
import sys
from pathlib import Path

TEMPLATE_DEFAULT_KEY = "django-insecure-CHANGE-ME"

# Mirrors Django's own security.W009 check exactly (see `_check_secret_key`
# in django/core/checks/security/base.py): a key must be at least this many
# characters long and use at least this many distinct characters, and must
# not carry Django's own auto-generated prefix. `manage.py check --deploy`
# runs right after this script in the same CI job — if the two rules do not
# agree, one guard says the key is fine while the other fails the build for
# the exact same key, which is worse than either guard alone: whoever reads
# the log has no way to tell which one to believe.
SECRET_KEY_MIN_LENGTH = 50
SECRET_KEY_MIN_UNIQUE_CHARACTERS = 5
SECRET_KEY_INSECURE_PREFIX = "django-insecure-"


def problems(settings):
    """Every reason this configuration must not go to production."""
    from django.core.exceptions import ImproperlyConfigured

    found = []
    if getattr(settings, "DEBUG", False):
        found.append("DEBUG 是開的。正式環境開著它，出錯時會把程式碼細節顯示給所有人看。")
    try:
        # `getattr(settings, "SECRET_KEY", default)` cannot fall back to
        # `default` here: Django's own LazySettings.__getattr__ raises
        # ImproperlyConfigured (not AttributeError) for an empty
        # SECRET_KEY, so the default value never gets a chance to apply.
        # Without this except, an unset key crashes with a raw traceback
        # instead of reaching the friendly message below — and this script
        # runs on every deploy, so that traceback is what the audience who
        # cannot read one would see.
        key = settings.SECRET_KEY
    except ImproperlyConfigured:
        key = ""
    if not key:
        found.append("SECRET_KEY 是空的。這把鑰匙用來簽登入狀態，沒有它任何人都能偽造登入。")
    elif key == TEMPLATE_DEFAULT_KEY or key.startswith(SECRET_KEY_INSECURE_PREFIX):
        found.append("SECRET_KEY 還是樣板的預設值。這個值是公開的，等於沒有鎖。")
    elif (
        len(key) < SECRET_KEY_MIN_LENGTH
        or len(set(key)) < SECRET_KEY_MIN_UNIQUE_CHARACTERS
    ):
        found.append(
            f"SECRET_KEY 太短或字元種類太少（Django 要求至少 {SECRET_KEY_MIN_LENGTH} 個字元、"
            f"至少 {SECRET_KEY_MIN_UNIQUE_CHARACTERS} 種不同字元）。這裡沒過的話，"
            "`manage.py check --deploy` 也一定會用同一個原因（security.W009）擋下來，"
            "所以現在先在這裡改好，換一把更長、更隨機的鑰匙。"
        )
    hosts = list(getattr(settings, "ALLOWED_HOSTS", []))
    if not hosts:
        found.append("ALLOWED_HOSTS 是空的，網站會拒絕所有連線。")
    elif "*" in hosts:
        found.append("ALLOWED_HOSTS 含有萬用字元，等於接受任何網址轉過來的請求。")
    return found


def main():
    # Running as `python scripts/check_deploy.py` puts scripts/ (not the
    # project root) on sys.path[0], so `import project` would fail. Put the
    # project root (this script's parent's parent) on sys.path first.
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    import django
    from django.conf import settings

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.prod")
    django.setup()

    found = problems(settings)
    if found:
        print("正式環境的設定有問題，先修好才能上線：")
        for item in found:
            print(f"  - {item}")
        return 1
    print("正式環境設定沒問題。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
