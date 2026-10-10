from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User 
from django.urls import reverse

class Post(models.Model) : 
    title = models.CharField(max_length=100)
    content = models.TextField()
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    #a partir d'ici c pour l'agent
    prompt = models.TextField(verbose_name="Preprompt") 
    profile_picture = models.ImageField(default='default_agent.jpg', upload_to='agent_pics')
    cooldown = models.IntegerField(default=5)
    CHOICES_AI = [
        ('local', 'Local Model: SmolLm-135M'),
        ('api', 'API Model')
    ]
    type_AI = models.CharField(
        max_length=7, 
        choices=CHOICES_AI, 
        default='local'
    )
    messages = models.TextField(default="", blank=True)
    last_activity = models.DateTimeField(default=timezone.now)

    def __str__(self) : 
        return self.title

    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk': self.pk})
