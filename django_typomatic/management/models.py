from django.db import models

'''
Create custom models to more complicated serializers (e.g. test nested fields).
'''


class AlbumStatusChoices(models.TextChoices):
    """Choices for album's status"""
    ARCHIVED = "1", "Archived"
    PRESAVED = "2", "Pre-saved"
    SAVED = "3", "Saved"
    LIKED = "4", "User's likes"
    DISLIKED = "5", "User's dislikes"
    NONE = "6", "None"


class Album(models.Model):
    album_name = models.CharField(max_length=100)
    artist = models.CharField(max_length=100)
    status = models.CharField(
        max_length=64,
        blank=False,
        editable=True,
        choices=AlbumStatusChoices.choices,
    )

    class Meta:
        app_label = 'django_typomatic'


class Track(models.Model):
    album = models.ForeignKey(Album, related_name='tracks', on_delete=models.CASCADE)
    order = models.IntegerField()
    title = models.CharField(max_length=100)
    duration = models.IntegerField()

    class Meta:
        app_label = 'django_typomatic'
        unique_together = ['album', 'order']
        ordering = ['order']

    def __str__(self):
        return '%d: %s' % (self.order, self.title)
