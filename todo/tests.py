from django.test import TestCase, Client
from django.utils import timezone
from datetime import datetime
from todo.models import Task


# Create your tests here.
class SampleTestCase(TestCase):
    def test_sample(self):
        self.assertEqual(1 + 2, 3)


class TaskModelTestCase(TestCase):
    def test_creat_task1(self):
        due = timezone.make_aware(datetime(2024, 6, 30, 23, 59, 59))
        task = Task(title='task1', due_at=due)
        task.save()
        task = Task.objects.get(pk=task.pk)
        self.assertEqual(task.title, 'task1')
        self.assertFalse(task.completed)
        self.assertEqual(task.due_at, due)

    def test_create_task2(self):
        task = Task(title='task2')
        task.save()

        task = Task.objects.get(pk=task.pk)
        self.assertEqual(task.title, 'task2')
        self.assertFalse(task.completed)
        self.assertEqual(task.due_at, None)

    def test_is_overdue_future(self):
        due = timezone.make_aware(datetime(2024, 6, 30, 23, 59, 59))
        current = timezone.make_aware(datetime(2024, 6, 30, 0, 0, 0))
        task = Task(title='task1', due_at=due)
        task.save()

        self.assertFalse(task.is_overdue(current))

    def test_is_overdue_past(self):
        due = timezone.make_aware(datetime(2024, 6, 30, 23, 59, 59))
        current = timezone.make_aware(datetime(2024, 7, 1, 0, 0, 0))
        task = Task(title='task1', due_at=due)
        task.save()

        self.assertTrue(task.is_overdue(current))

    def test_is_overdue_none(self):
        current = timezone.make_aware(datetime(2024, 7, 1, 0, 0, 0))
        task = Task(title='task1', due_at=None)
        task.save()

        self.assertFalse(task.is_overdue(current))


class TodoViewTestCase(TestCase):
    def test_index_get(self):
        client = Client()
        response = client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'todo/index.html')
        self.assertEqual(len(response.context['tasks']), 0)

    def test_index_post(self):
        client = Client()
        data = {'title': 'Test Task', 'due_at': '2024-06-30 23:59:59'}
        response = client.post('/', data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'todo/index.html')
        self.assertEqual(len(response.context['tasks']), 1)

    def test_index_post_without_due_at(self):
        client = Client()
        response = client.post('/', {'title': 'No due date', 'due_at': ''})

        self.assertEqual(response.status_code, 200)
        task = Task.objects.get(title='No due date')
        self.assertIsNone(task.due_at)

    def test_index_post_with_long_title(self):
        client = Client()
        response = client.post('/', {'title': 'x' * 101, 'due_at': ''})

        self.assertEqual(response.status_code, 200)
        task = Task.objects.get()
        self.assertEqual(task.title, 'x' * 100)

    def test_index_get_order_post(self):
        task1 = Task(title='task1', due_at=timezone.make_aware(datetime(2024, 7, 1)))
        task1.save()
        task2 = Task(title='task2', due_at=timezone.make_aware(datetime(2024, 8, 1)))
        task2.save()
        client = Client()
        response = client.get('/?order=post')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'todo/index.html')
        self.assertEqual(response.context['tasks'][0], task2)
        self.assertEqual(response.context['tasks'][1], task1)

    def test_index_get_order_due(self):
        task1 = Task(title='task1', due_at=timezone.make_aware(datetime(2024, 7, 1)))
        task1.save()
        task2 = Task(title='task2', due_at=timezone.make_aware(datetime(2024, 8, 1)))
        task2.save()
        client = Client()
        response = client.get('/?order=due')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'todo/index.html')
        self.assertEqual(response.context['tasks'][0], task1)
        self.assertEqual(response.context['tasks'][1], task2)

    def test_detail_get_success(self):
        task = Task(title='task1', due_at=timezone.make_aware(datetime(2024, 7, 1)))
        task.save()
        client = Client()
        response = client.get('/{}/'.format(task.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'todo/detail.html')
        self.assertEqual(response.context['task'], task)
        self.assertContains(response, '<form action="/{}/close" method="post"'.format(task.pk))
        self.assertContains(response, '<button class="button button-primary" type="submit">完了にする</button>')
        self.assertNotContains(response, '<a class="button button-primary" href="/{}/close">完了にする</a>'.format(task.pk))

    def test_detail_get_fail(self):
        client = Client()
        response = client.get('/1/')

        self.assertEqual(response.status_code, 404)

    def test_update_without_due_at(self):
        task = Task.objects.create(
            title='task1',
            due_at=timezone.make_aware(datetime(2024, 7, 1)),
        )
        client = Client()
        response = client.post(
            '/{}/update'.format(task.pk),
            {'title': 'task1 updated', 'due_at': ''},
        )

        self.assertRedirects(response, '/{}/'.format(task.pk))
        task.refresh_from_db()
        self.assertEqual(task.title, 'task1 updated')
        self.assertIsNone(task.due_at)

    def test_close_success(self):
        task = Task(title='task1')
        task.save()
        client = Client()
        response = client.post('/{}/close'.format(task.pk))

        self.assertEqual(response.status_code, 302)
        task.refresh_from_db()
        self.assertTrue(task.completed)

    def test_close_success_with_trailing_slash(self):
        task = Task(title='task1')
        task.save()
        client = Client()
        response = client.post('/{}/close/'.format(task.pk))

        self.assertEqual(response.status_code, 302)
        task.refresh_from_db()
        self.assertTrue(task.completed)

    def test_close_fail(self):
        client = Client()
        response = client.post('/1/close')

        self.assertEqual(response.status_code, 404)

    def test_close_get_not_allowed(self):
        task = Task(title='task1')
        task.save()
        client = Client()
        response = client.get('/{}/close'.format(task.pk))

        self.assertEqual(response.status_code, 405)
        task.refresh_from_db()
        self.assertFalse(task.completed)

    def test_delete_get_shows_confirmation(self):
        task = Task(title='task1', due_at=timezone.make_aware(datetime(2024, 7, 1)))
        task.save()
        client = Client()
        response = client.get('/{}/delete'.format(task.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'todo/delete.html')
        self.assertEqual(response.context['task'], task)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    def test_delete_post_success(self):
        task = Task.objects.create(title='task1')
        client = Client()
        response = client.post('/{}/delete'.format(task.pk))

        self.assertRedirects(response, '/')
        with self.assertRaises(Task.DoesNotExist):
            Task.objects.get(pk=task.pk)

    def test_delete_get_fail(self):
        client = Client()
        response = client.get('/1/delete')

        self.assertEqual(response.status_code, 404)

    def test_update_get(self):
        task = Task(title='task1', due_at=timezone.make_aware(datetime(2024, 7, 1)))
        task.save()
        client = Client()
        response = client.get('/{}/update'.format(task.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'todo/edit.html')
        self.assertEqual(response.context['task'], task)
        self.assertContains(response, 'maxlength="100"')

    def test_update_post(self):
        task = Task(title='task1', due_at=timezone.make_aware(datetime(2024, 7, 1)))
        task.save()
        client = Client()
        data = {
            'title': 'updated task',
            'due_at': '2024-08-01 12:00:00'
        }
        response = client.post('/{}/update'.format(task.pk), data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/{}/'.format(task.pk))

        task.refresh_from_db()
        self.assertEqual(task.title, 'updated task')
        self.assertEqual(task.due_at, timezone.make_aware(datetime(2024, 8, 1, 12, 0, 0)))

    def test_update_post_with_long_title(self):
        task = Task(title='task1')
        task.save()
        client = Client()
        response = client.post('/{}/update'.format(task.pk), {'title': 'x' * 101, 'due_at': ''})

        self.assertEqual(response.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.title, 'x' * 100)

    def test_calendar_get_for_selected_month(self):
        task = Task.objects.create(
            title='calendar task',
            due_at=timezone.make_aware(datetime(2026, 7, 16, 14, 30)),
        )
        response = self.client.get('/calendar/?year=2026&month=7')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'todo/calendar.html')
        self.assertEqual(response.context['current_month'].year, 2026)
        self.assertEqual(response.context['current_month'].month, 7)
        days = [day for week in response.context['calendar_weeks'] for day in week]
        target_day = next(day for day in days if day['date'].day == 16 and day['in_month'])
        self.assertEqual(target_day['tasks'], [task])
        self.assertContains(response, 'calendar task')
        self.assertContains(response, 'href="/{}"'.format(task.pk))

    def test_calendar_month_navigation_across_year(self):
        response = self.client.get('/calendar/?year=2026&month=12')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['previous_month'].year, 2026)
        self.assertEqual(response.context['previous_month'].month, 11)
        self.assertEqual(response.context['next_month'].year, 2027)
        self.assertEqual(response.context['next_month'].month, 1)

    def test_calendar_invalid_month_falls_back_to_current_month(self):
        response = self.client.get('/calendar/?year=invalid&month=20')
        today = timezone.localdate()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_month'].year, today.year)
        self.assertEqual(response.context['current_month'].month, today.month)

    def test_calendar_shows_undated_tasks_separately(self):
        undated_task = Task.objects.create(title='undated task')
        response = self.client.get('/calendar/?year=2026&month=7')

        self.assertContains(response, 'undated task')
        self.assertIn(undated_task, response.context['undated_tasks'])

    def test_calendar_marks_completed_task(self):
        Task.objects.create(
            title='completed calendar task',
            completed=True,
            due_at=timezone.make_aware(datetime(2026, 7, 16, 14, 30)),
        )
        response = self.client.get('/calendar/?year=2026&month=7')

        self.assertContains(response, 'calendar-task-completed')
