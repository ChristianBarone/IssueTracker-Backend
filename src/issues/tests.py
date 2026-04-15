from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Issue, IssueActivity


class WatcherActivityTests(TestCase):
	def setUp(self):
		self.actor = User.objects.create_user(username='actor', password='secret123')
		self.target = User.objects.create_user(username='target', password='secret123')
		self.issue = Issue.objects.create(
			subject='Issue to test watcher activity',
			description='desc',
			creator=self.actor,
			assignee=self.actor,
			issue_type='Bug',
			issue_severity='Normal',
			priority='Normal',
			status='New',
		)

	def test_add_watcher_creates_activity(self):
		self.client.force_login(self.actor)

		response = self.client.post(
			reverse('add_watcher', args=[self.issue.id]),
			{'user_id': self.target.id},
		)

		self.assertEqual(response.status_code, 302)
		self.assertTrue(self.issue.watchers.filter(id=self.target.id).exists())

		activity = IssueActivity.objects.filter(issue=self.issue, field_name='watchers').latest('created_at')
		self.assertEqual(activity.actor, self.actor)
		self.assertEqual(activity.new_value, f'added @{self.target.username}')

	def test_toggle_remove_watcher_creates_activity(self):
		self.issue.watchers.add(self.target)
		self.client.force_login(self.actor)

		response = self.client.post(
			reverse('toggle_watcher', args=[self.issue.id]),
			{'user_id': self.target.id},
		)

		self.assertEqual(response.status_code, 302)
		self.assertFalse(self.issue.watchers.filter(id=self.target.id).exists())

		activity = IssueActivity.objects.filter(issue=self.issue, field_name='watchers').latest('created_at')
		self.assertEqual(activity.actor, self.actor)
		self.assertEqual(activity.new_value, f'removed @{self.target.username}')
