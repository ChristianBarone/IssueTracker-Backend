from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Issue, IssueActivity


class IssueAssignmentAndWatcherTests(TestCase):
	def setUp(self):
		self.actor = User.objects.create_user(username='actor', password='secret123')
		self.target = User.objects.create_user(username='target', password='secret123')
		self.issue = Issue.objects.create(
			subject='Issue to test assignment and watcher activity',
			description='desc',
			creator=self.actor,
		)

	def test_default_issue_assignee_is_unassigned(self):
		self.assertIsNone(self.issue.assignee)

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

	def test_assign_issue_to_another_user_creates_activity(self):
		self.client.force_login(self.actor)

		response = self.client.post(
			reverse('issue_update_assignee', args=[self.issue.id]),
			{'assignee_id': self.target.id},
		)

		self.assertEqual(response.status_code, 302)
		self.issue.refresh_from_db()
		self.assertEqual(self.issue.assignee, self.target)

		activity = IssueActivity.objects.filter(issue=self.issue, field_name='assignee').latest('created_at')
		self.assertEqual(activity.actor, self.actor)
		self.assertEqual(activity.old_value, 'Unassigned')
		self.assertEqual(activity.new_value, f'@{self.target.username}')

	def test_assign_issue_to_self_creates_activity(self):
		self.client.force_login(self.actor)

		response = self.client.post(
			reverse('issue_update_assignee', args=[self.issue.id]),
			{'assignee_id': self.actor.id},
		)

		self.assertEqual(response.status_code, 302)
		self.issue.refresh_from_db()
		self.assertEqual(self.issue.assignee, self.actor)

	def test_unassign_issue_creates_activity(self):
		self.issue.assignee = self.target
		self.issue.save(update_fields=['assignee'])
		self.client.force_login(self.actor)

		response = self.client.post(
			reverse('issue_update_assignee', args=[self.issue.id]),
			{'assignee_id': ''},
		)

		self.assertEqual(response.status_code, 302)
		self.issue.refresh_from_db()
		self.assertIsNone(self.issue.assignee)

		activity = IssueActivity.objects.filter(issue=self.issue, field_name='assignee').latest('created_at')
		self.assertEqual(activity.old_value, f'@{self.target.username}')
		self.assertEqual(activity.new_value, 'Unassigned')

	def test_issue_list_can_filter_unassigned(self):
		self.issue.assignee = self.actor
		self.issue.save(update_fields=['assignee'])
		unassigned_issue = Issue.objects.create(
			subject='Unassigned issue',
			description='desc',
			creator=self.actor,
		)

		self.client.force_login(self.actor)
		response = self.client.get(reverse('issue_list'), {'assigned_to': 'unassigned'})

		self.assertEqual(response.status_code, 200)
		returned_issue_ids = {issue.id for issue in response.context['issues']}
		self.assertIn(unassigned_issue.id, returned_issue_ids)
		self.assertNotIn(self.issue.id, returned_issue_ids)
