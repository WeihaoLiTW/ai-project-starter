import pytest


@pytest.mark.django_db
def test_a_saved_note_can_be_read_back_again():
    """存進去的一筆「紀錄」，再讀出來還在。"""
    from core.models import Note

    Note.objects.create(body="第一筆")

    assert Note.objects.get().body == "第一筆"


@pytest.mark.django_db
def test_the_health_page_answers(client):
    """打開健康檢查網址，回 200。"""
    assert client.get("/health/").status_code == 200
