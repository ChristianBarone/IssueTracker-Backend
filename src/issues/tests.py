import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .helpers import update_issue_assignee
from .models import Issue, IssueActivity, Profile


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
            reverse('watcher_add', args=[self.issue.pk]),
            {'user_id': self.target.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.issue.watchers.filter(pk=self.target.pk).exists())

        activity = IssueActivity.objects.filter(issue=self.issue, field_name='watchers').latest('created_at')
        self.assertEqual(activity.actor, self.actor)
        self.assertEqual(activity.new_value, f'added @{self.target.username}')

    def test_toggle_remove_watcher_creates_activity(self):
        self.issue.watchers.add(self.target)
        self.client.force_login(self.actor)

        response = self.client.post(
            reverse('remove_watcher', args=[self.issue.pk]),
            {'user_id': self.target.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.issue.watchers.filter(pk=self.target.pk).exists())

        activity = IssueActivity.objects.filter(issue=self.issue, field_name='watchers').latest('created_at')
        self.assertEqual(activity.actor, self.actor)
        self.assertEqual(activity.new_value, f'removed @{self.target.username}')

    def test_assign_issue_to_another_user_creates_activity(self):
        self.client.force_login(self.actor)

        response = self.client.post(
            reverse('issue_update_assignee', args=[self.issue.pk]),
            {'assignee_id': self.target.pk},
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
            reverse('issue_update_assignee', args=[self.issue.pk]),
            {'assignee_id': self.actor.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.assignee, self.actor)

    def test_unassign_issue_creates_activity(self):
        self.issue.assignee = self.target
        self.issue.save(update_fields=['assignee'])
        self.client.force_login(self.actor)

        response = self.client.post(
            reverse('issue_update_assignee', args=[self.issue.pk]),
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
        returned_issue_ids = {issue.pk for issue in response.context['issues']}
        self.assertIn(unassigned_issue.pk, returned_issue_ids)
        self.assertNotIn(self.issue.pk, returned_issue_ids)

    def test_profile_watched_tab_shows_watched_issues(self):
        watched_issue = Issue.objects.create(
            subject='Watched issue',
            description='desc',
            creator=self.target,
        )
        watched_issue.watchers.add(self.actor)

        other_issue = Issue.objects.create(
            subject='Not watched issue',
            description='desc',
            creator=self.target,
        )
        other_issue.watchers.add(self.target)

        response = self.client.get(
            reverse('profile_view', args=[self.actor.username]),
            {'tab': 'watched'},
        )

        self.assertEqual(response.status_code, 200)
        returned_issue_ids = {issue.pk for issue in response.context['items']}
        self.assertIn(watched_issue.pk, returned_issue_ids)
        self.assertNotIn(other_issue.pk, returned_issue_ids)
        self.assertEqual(response.context['watched_issues'], 1)

    def test_issue_create_assigns_selected_user(self):
        self.client.force_login(self.actor)
        response = self.client.post(reverse('issue_create'), {
            'subject': 'Create with selected assignee',
            'description': 'desc',
            'issue_type': 'Bug',
            'issue_severity': 'Normal',
            'priority': 'Normal',
            'status': 'New',
            'assignee_id': str(self.target.pk),
        })

        self.assertEqual(response.status_code, 302)
        created_issue = Issue.objects.get(subject='Create with selected assignee')
        self.assertEqual(created_issue.assignee, self.target)

    def test_issue_create_without_assignee_stays_unassigned(self):
        self.client.force_login(self.actor)
        response = self.client.post(reverse('issue_create'), {
            'subject': 'Create unassigned issue',
            'description': 'desc',
            'issue_type': 'Bug',
            'issue_severity': 'Normal',
            'priority': 'Normal',
            'status': 'New',
            'assignee_id': '',
        })

        self.assertEqual(response.status_code, 302)
        created_issue = Issue.objects.get(subject='Create unassigned issue')
        self.assertIsNone(created_issue.assignee)

    def test_helper_assign_from_unassigned(self):
        changed = update_issue_assignee(self.issue, self.target, self.actor)

        self.assertTrue(changed)
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.assignee, self.target)

        activity = IssueActivity.objects.filter(issue=self.issue, field_name='assignee').latest('created_at')
        self.assertEqual(activity.old_value, 'Unassigned')
        self.assertEqual(activity.new_value, f'@{self.target.username}')

    def test_helper_unassign(self):
        self.issue.assignee = self.target
        self.issue.save()

        changed = update_issue_assignee(self.issue, None, self.actor)

        self.assertTrue(changed)
        self.issue.refresh_from_db()
        self.assertIsNone(self.issue.assignee)

        activity = IssueActivity.objects.filter(issue=self.issue, field_name='assignee').latest('created_at')
        self.assertEqual(activity.old_value, f'@{self.target.username}')
        self.assertEqual(activity.new_value, 'Unassigned')

    def test_helper_no_change_does_not_create_activity(self):
        self.issue.assignee = self.target
        self.issue.save()

        before_count = IssueActivity.objects.count()

        changed = update_issue_assignee(self.issue, self.target, self.actor)

        self.assertFalse(changed)
        self.assertEqual(IssueActivity.objects.count(), before_count)

    def test_api_assign_user(self):
        self.client.force_login(self.actor)

        response = self.client.post(
            reverse('issue_update_assignee', args=[self.issue.pk]),
            data=json.dumps({'assignee_id': self.target.pk}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)

        self.issue.refresh_from_db()
        self.assertEqual(self.issue.assignee, self.target)

        data = response.json()
        self.assertEqual(data['assignee'], self.target.username)

    def test_api_unassign(self):
        self.issue.assignee = self.target
        self.issue.save()

        self.client.force_login(self.actor)

        response = self.client.post(
            reverse('issue_update_assignee', args=[self.issue.pk]),
            data=json.dumps({'assignee_id': ''}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)

        self.issue.refresh_from_db()
        self.assertIsNone(self.issue.assignee)

        data = response.json()
        self.assertEqual(data['assignee'], 'Unassigned')

    def test_api_invalid_assignee(self):
        self.client.force_login(self.actor)

        response = self.client.post(
            reverse('issue_update_assignee', args=[self.issue.pk]),
            data=json.dumps({'assignee_id': 99999}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        
class ProfileWebTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            password='test123'
        )

        self.profile = Profile.objects.get(user=self.user)
        self.profile.bio = 'hello'
        self.profile.save()

    def test_profile_view_web(self):
        response = self.client.get(
            reverse('profile_view', args=[self.user.username]),
            HTTP_ACCEPT='text/html'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alice')

    def test_profile_edit_requires_login(self):
        response = self.client.get(
            reverse('profile_edit', args=[self.user.username]),
            HTTP_ACCEPT='text/html'
        )

        self.assertEqual(response.status_code, 302)

    def test_profile_edit_web(self):
        self.client.login(
            username='alice',
            password='test123'
        )

        response = self.client.post(
            reverse('profile_edit', args=[self.user.username]),
            {
                'bio': 'new bio'
            },
            HTTP_ACCEPT='text/html'
        )

        self.assertEqual(response.status_code, 302)

        self.profile.refresh_from_db()

        self.assertEqual(self.profile.bio, 'new bio')

    def test_profile_edit_forbidden_for_other_user(self):
        other = User.objects.create_user(
            username='bob',
            password='test123'
        )

        self.client.login(
            username='bob',
            password='test123'
        )

        response = self.client.post(
            reverse('profile_edit', args=[self.user.username]),
            {
                'bio': 'hacked'
            },
            HTTP_ACCEPT='text/html'
        )

        self.assertEqual(response.status_code, 302)

        self.profile.refresh_from_db()

        self.assertNotEqual(self.profile.bio, 'hacked')


class ProfileApiTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            password='test123'
        )

        self.profile = Profile.objects.get(user=self.user)
        self.profile.api_key = 'abc123'
        self.profile.bio = 'hello'
        self.profile.save()

    def test_profile_view_api(self):
        response = self.client.get(
            reverse('profile_view', args=[self.user.username]),
            HTTP_ACCEPT='application/json',
            HTTP_AUTHORIZATION='abc123'
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['username'], 'alice')

    def test_profile_edit_api(self):
        response = self.client.post(
            reverse('profile_edit', args=[self.user.username]),
            data=json.dumps({
                'bio': 'updated bio'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION='abc123'
        )

        self.assertEqual(response.status_code, 200)

        self.profile.refresh_from_db()

        self.assertEqual(self.profile.bio, 'updated bio')

    def test_profile_edit_invalid_api_key(self):
        response = self.client.post(
            reverse('profile_edit', args=[self.user.username]),
            data=json.dumps({
                'bio': 'updated bio'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION='wrongkey'
        )

        self.assertEqual(response.status_code, 401)

    def test_profile_edit_other_user_forbidden(self):
        other = User.objects.create_user(
            username='bob',
            password='test123'
        )

        other_profile = Profile.objects.get(user=other)
        other_profile.api_key = 'bobkey'
        other_profile.save()

        response = self.client.post(
            reverse('profile_edit', args=[self.user.username]),
            data=json.dumps({
                'bio': 'hack'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION='bobkey'
        )

        self.assertEqual(response.status_code, 403)