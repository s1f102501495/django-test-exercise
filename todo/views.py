import calendar
from datetime import datetime

from django.shortcuts import render, redirect
from django.http import Http404
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
from django.utils.timezone import make_aware
from django.utils.dateparse import parse_datetime
from todo.models import Task


def parse_title(value):
    max_length = Task._meta.get_field('title').max_length
    return (value or '')[:max_length]


def parse_due_at(value):
    if not value:
        return None

    due_at = parse_datetime(value)
    if due_at is None:
        return None
    if due_at.utcoffset() is None:
        return make_aware(due_at)
    return due_at


# Create your views here.
def index(request):
    if request.method == 'POST':
        task = Task(
            title=parse_title(request.POST.get('title')),
            due_at=parse_due_at(request.POST.get('due_at')),
        )
        task.save()

    if request.GET.get('order') == 'due':
        tasks = Task.objects.order_by('due_at')
    else:
        tasks = Task.objects.order_by('-posted_at')

    context = {
        'tasks': tasks
    }
    return render(request, 'todo/index.html', context)


def calendar_view(request):
    today = timezone.localdate()

    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        if not 2 <= year <= 9998:
            raise ValueError
        current_month = datetime(year, month, 1).date()
    except (TypeError, ValueError):
        current_month = today.replace(day=1)

    if current_month.month == 1:
        previous_month = current_month.replace(year=current_month.year - 1, month=12)
    else:
        previous_month = current_month.replace(month=current_month.month - 1)

    if current_month.month == 12:
        next_month = current_month.replace(year=current_month.year + 1, month=1)
    else:
        next_month = current_month.replace(month=current_month.month + 1)

    month_calendar = calendar.Calendar(firstweekday=calendar.MONDAY)
    dates = month_calendar.monthdatescalendar(current_month.year, current_month.month)
    tasks_by_date = {}
    tasks = Task.objects.filter(
        due_at__date__gte=dates[0][0],
        due_at__date__lte=dates[-1][-1],
    ).order_by('due_at', 'posted_at')

    for task in tasks:
        due_date = timezone.localtime(task.due_at).date()
        tasks_by_date.setdefault(due_date, []).append(task)

    calendar_weeks = [
        [
            {
                'date': day,
                'in_month': day.month == current_month.month,
                'is_today': day == today,
                'tasks': tasks_by_date.get(day, []),
            }
            for day in week
        ]
        for week in dates
    ]

    context = {
        'calendar_weeks': calendar_weeks,
        'current_month': current_month,
        'previous_month': previous_month,
        'next_month': next_month,
        'today': today,
        'undated_tasks': Task.objects.filter(due_at__isnull=True).order_by('-posted_at'),
        'weekdays': ['月', '火', '水', '木', '金', '土', '日'],
    }
    return render(request, 'todo/calendar.html', context)


def detail(request, task_id):
    try:
        task = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        raise Http404("Task does not exist")

    context = {
        'task': task,
    }
    return render(request, 'todo/detail.html', context)


@require_POST
def close(request, task_id):
    try:
        task = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        raise Http404("Task does not exist")
    task.completed = True
    task.save()
    return redirect(index)


def update(request, task_id):
    try:
        task = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        raise Http404("Task does not exist")
    if request.method == 'POST':
        task.title = parse_title(request.POST.get('title', task.title))
        task.due_at = parse_due_at(request.POST.get('due_at'))
        task.save()
        return redirect(f'/{task.id}/')

    context = {
        'task': task,
    }
    return render(request, 'todo/edit.html', context)


@require_http_methods(['GET', 'POST'])
def delete(request, task_id):
    try:
        task = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        raise Http404("Task does not exist")
    if request.method == 'POST':
        task.delete()
        return redirect(index)

    context = {
        'task': task,
    }
    return render(request, 'todo/delete.html', context)
