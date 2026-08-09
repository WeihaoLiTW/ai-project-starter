from django.db import models


class Note(models.Model):
    """A single line of text. The health check writes its marker here."""

    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.body[:40]
