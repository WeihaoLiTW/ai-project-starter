"""Refuse to deploy a production configuration that is unsafe.

Django's own deploy check covers DEBUG and the insecure default key, but it
only flags an ALLOWED_HOSTS that is empty. A wildcard passes its check and
fails ours.
"""

import os
import sys
from pathlib import Path

TEMPLATE_DEFAULT_KEY = "django-insecure-CHANGE-ME"


def problems(settings):
    """Every reason this configuration must not go to production."""
    found = []
    if getattr(settings, "DEBUG", False):
        found.append("DEBUG 是開的。正式環境開著它，出錯時會把程式碼細節顯示給所有人看。")
    key = getattr(settings, "SECRET_KEY", "")
    if not key:
        found.append("SECRET_KEY 是空的。這把鑰匙用來簽登入狀態，沒有它任何人都能偽造登入。")
    elif key == TEMPLATE_DEFAULT_KEY or key.startswith("django-insecure-"):
        found.append("SECRET_KEY 還是樣板的預設值。這個值是公開的，等於沒有鎖。")
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
