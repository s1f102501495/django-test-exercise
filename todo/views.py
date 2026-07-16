from django.shortcuts import render, redirect
from django.http import Http404
from django.views.decorators.http import require_http_methods, require_POST
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

    filter_mode = request.GET.get('filter', 'all')
    if filter_mode == 'active':
        tasks = Task.objects.filter(completed=False)
    else:
        tasks = Task.objects.all()

    if request.GET.get('order') == 'due':
        tasks = tasks.order_by('due_at')
    else:
        tasks = tasks.order_by('-posted_at')

    context = {
        'tasks': tasks,
        'filter_mode': filter_mode,
    }
    return render(request, 'todo/index.html', context)


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
