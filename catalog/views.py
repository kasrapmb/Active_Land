from django.db.models import Prefetch
from django.shortcuts import render
from .models import ClassType, Session

def home(request):
    classes = list(ClassType.objects.filter(active=True).prefetch_related(Prefetch('sessions', queryset=Session.objects.filter(active=True))))
    schedule = {item.slug: {'name': item.name, 'slots': [{'label': f'{slot.get_weekday_display()} · {slot.start_time:%H:%M} تا {slot.end_time:%H:%M}', 'url': f'/registration/session/{slot.pk}/'} for slot in item.sessions.all()]} for item in classes}
    return render(request, 'catalog/home.html', {'classes': classes, 'schedule': schedule})
