from django.test import TestCase
from django.urls import reverse
from accounts.models import User


class UserRegistrationTests(TestCase):
    def test_signup_creates_viewer_with_contact(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'contact': '1234567890',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
        })
        # registration redirects to login when successful
        self.assertRedirects(response, reverse('login'))
        user = User.objects.get(username='newuser')
        self.assertEqual(user.role, 'VIEWER')
        self.assertEqual(user.contact, '1234567890')
        self.assertFalse(user.created_by_admin)


class DashboardVisibilityTests(TestCase):
    def setUp(self):
        # create different types of users.  we deliberately include one manager
        # that simulates being created through the admin form (created_by_admin
        # flag set) so we can catch regressions when the dashboard query filters
        # it out.
        self.admin = User.objects.create_superuser('admin', 'a@a.com', 'pass')
        # normal signup manager; we'll mark it as having been added by an
        # admin so that the superuser sees it even though the dashboard used to
        # filter such users.  We avoid creating a second manager because the
        # User.save() logic enforces unique roles and would downgrade the first
        # one to VIEWER if a second manager appears.
        self.manager = User.objects.create(username='mgr', password='pass', role='MANAGER')
        self.manager.created_by_admin = True
        self.manager.save()

        self.viewer_signup = User.objects.create(username='v1', password='pass', role='VIEWER')
        self.viewer_signup.created_by_admin = False
        self.viewer_signup.save()
        self.viewer_admin = User.objects.create(username='v2', password='pass', role='VIEWER')
        self.viewer_admin.created_by_admin = True
        self.viewer_admin.save()

    def login_as(self, user):
        self.client.force_login(user)

    def test_admin_sees_everyone_except_self(self):
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard'))
        # admin should see signup users and the manager entry regardless of the
        # created_by_admin flag, plus any other admin‑added viewers.
        self.assertContains(resp, 'v1')
        self.assertContains(resp, 'mgr')
        self.assertContains(resp, 'v2')

    def test_manager_sees_all_non_admin_users(self):
        self.login_as(self.manager)
        resp = self.client.get(reverse('dashboard'))
        # after the recent change managers should see everyone except the
        # superuser (and themselves, which is filtered by the view logic).
        self.assertContains(resp, 'v1')
        self.assertContains(resp, 'v2')
        self.assertNotContains(resp, 'admin')

    def test_viewer_sees_others_excluding_admin_manager(self):
        self.login_as(self.viewer_signup)
        resp = self.client.get(reverse('dashboard'))
        # manager is a 'MANAGER' role so viewer should not see them
        self.assertNotContains(resp, 'mgr')
        self.assertContains(resp, 'v2')

    def test_users_sorted_by_role_priority(self):
        # create additional records to verify ordering
        editor = User.objects.create(username='ed', password='pass', role='EDITOR')
        hybrid = User.objects.create(username='hb', password='pass', role='HYBRID')
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard'))
        # inspect context queryset (Django test client provides it)
        users = resp.context['users']
        usernames = [u.username for u in users]
        # expected relative order: manager -> editor -> hybrid -> viewer signup (v1) -> viewer admin (v2)
        self.assertLess(usernames.index('mgr'), usernames.index('ed'))
        self.assertLess(usernames.index('ed'), usernames.index('hb'))
        self.assertLess(usernames.index('hb'), usernames.index('v1'))

    def test_superuser_can_edit_self(self):
        # navigate to edit page and post updated email/contact
        self.login_as(self.admin)
        url = reverse('edit_user', args=[self.admin.id])
        resp_get = self.client.get(url)
        self.assertEqual(resp_get.status_code, 200)
        data = {
            'username': 'admin',
            'email': 'newadmin@example.com',
            'contact': '999-888-7777',
        }
        resp_post = self.client.post(url, data)
        # after edit should redirect to dashboard
        self.assertRedirects(resp_post, reverse('dashboard'))
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.email, 'newadmin@example.com')
        self.assertEqual(self.admin.contact, '999-888-7777')


class UserDeleteTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'a@a.com', 'pass')
        self.manager = User.objects.create(username='mgr', password='pass', role='MANAGER')
        self.editor = User.objects.create(username='editor', password='pass', role='EDITOR')
        self.hybrid = User.objects.create(username='hybrid', password='pass', role='HYBRID')
        self.viewer = User.objects.create(username='viewer1', password='pass', role='VIEWER')
        self.viewer.created_by_admin = False
        self.viewer.save()

    def login_as(self, user):
        self.client.force_login(user)

    def test_admin_can_delete_non_superuser(self):
        self.login_as(self.admin)
        resp = self.client.post(reverse('delete_user', args=[self.viewer.id]))
        self.assertRedirects(resp, reverse('dashboard'))
        self.assertFalse(User.objects.filter(id=self.viewer.id).exists())

    def test_admin_cannot_delete_self(self):
        self.login_as(self.admin)
        resp = self.client.post(reverse('delete_user', args=[self.admin.id]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())

    def test_manager_can_delete_viewer(self):
        self.login_as(self.manager)
        resp = self.client.post(reverse('delete_user', args=[self.viewer.id]))
        self.assertRedirects(resp, reverse('dashboard'))
        self.assertFalse(User.objects.filter(id=self.viewer.id).exists())

    def test_manager_can_delete_editor(self):
        self.login_as(self.manager)
        resp = self.client.post(reverse('delete_user', args=[self.editor.id]))
        self.assertRedirects(resp, reverse('dashboard'))
        self.assertFalse(User.objects.filter(id=self.editor.id).exists())

    def test_editor_cannot_delete_anyone(self):
        viewer2 = User.objects.create(username='viewer2', password='pass', role='VIEWER')
        self.login_as(self.editor)
        resp = self.client.post(reverse('delete_user', args=[viewer2.id]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(User.objects.filter(id=viewer2.id).exists())

    def test_hybrid_cannot_delete_anyone(self):
        viewer2 = User.objects.create(username='viewer2', password='pass', role='VIEWER')
        self.login_as(self.hybrid)
        resp = self.client.post(reverse('delete_user', args=[viewer2.id]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(User.objects.filter(id=viewer2.id).exists())

    def test_viewer_cannot_delete_anyone(self):
        viewer2 = User.objects.create(username='viewer2', password='pass', role='VIEWER')
        self.login_as(self.viewer)
        resp = self.client.post(reverse('delete_user', args=[viewer2.id]))
        self.assertEqual(resp.status_code, 403)

    def test_manager_cannot_delete_other_manager(self):
        # due to the unique-role logic in User.save(), creating a second manager
        # automatically downgrades the first one to VIEWER, so in practice a
        # logged‑in manager will never see another manager with that role.  the
        # view should still prevent deletion if somehow the role is MANAGER.
        manager2 = User.objects.create(username='mgr2', password='pass', role='MANAGER')
        self.login_as(self.manager)
        resp = self.client.post(reverse('delete_user', args=[manager2.id]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(User.objects.filter(id=manager2.id).exists())


# additional permission-related tests
class AccountPermissionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'a@a.com', 'pass')
        self.manager = User.objects.create(username='mgr', password='pass', role='MANAGER')
        self.editor = User.objects.create(username='editor', password='pass', role='EDITOR')
        self.viewer = User.objects.create(username='viewer', password='pass', role='VIEWER')
        self.viewer.created_by_admin = False
        self.viewer.save()

    def login_as(self, user):
        self.client.force_login(user)

    def test_editor_cannot_access_create_user(self):
        self.login_as(self.editor)
        resp = self.client.get(reverse('create_user'))
        self.assertEqual(resp.status_code, 403)

    def test_manager_can_access_create_user(self):
        self.login_as(self.manager)
        resp = self.client.get(reverse('create_user'))
        self.assertEqual(resp.status_code, 200)
        # role and department fields should be present for managers
        self.assertContains(resp, 'name="role"')
        self.assertContains(resp, 'name="department"')

    def test_manager_edit_form_shows_role_and_department(self):
        self.login_as(self.manager)
        url = reverse('edit_user', args=[self.viewer.id])
        resp = self.client.get(url)
        self.assertContains(resp, 'name="role"')
        self.assertContains(resp, 'name="department"')

    def test_editor_edit_form_hides_role_and_department(self):
        self.login_as(self.editor)
        url = reverse('edit_user', args=[self.viewer.id])
        resp = self.client.get(url)
        self.assertContains(resp, 'name="username"')
        self.assertContains(resp, 'name="email"')
        self.assertContains(resp, 'name="contact"')
        self.assertNotContains(resp, 'name="role"')
        self.assertNotContains(resp, 'name="department"')


class DashboardSearchTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        self.viewer1 = User.objects.create(username='john_doe', email='john@example.com', password='pass', role='VIEWER')
        self.viewer1.created_by_admin = False
        self.viewer1.save()
        self.viewer2 = User.objects.create(username='alice_smith', email='alice@test.org', password='pass', role='VIEWER')
        self.viewer2.created_by_admin = False
        self.viewer2.save()
        # create some tickets for search tests
        from tickets.models import Ticket
        # ticket visible to viewer1 only
        from accounts.models import Department
        # ensure departments exist
        it_dept = Department.objects.get_or_create(name='IT')[0]
        hr_dept = Department.objects.get_or_create(name='HR')[0]
        self.ticket1 = Ticket.objects.create(
            title='Alpha Issue', description='first ticket', department=it_dept, project_name='Alpha'
        )
        self.ticket1.assignee = self.viewer1
        self.ticket1.save()
        # ticket visible to viewer2 only
        self.ticket2 = Ticket.objects.create(
            title='Beta Problem', description='second ticket', department=hr_dept, project_name='Beta'
        )
        self.ticket2.assignee = self.viewer2
        self.ticket2.save()

    def login_as(self, user):
        self.client.force_login(user)

    def test_search_by_username(self):
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard') + '?search=john')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'john_doe')
        self.assertNotContains(resp, 'alice_smith')

    def test_search_by_email(self):
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard') + '?search=alice@test.org')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'alice_smith')
        self.assertNotContains(resp, 'john_doe')

    def test_search_no_results(self):
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard') + '?search=nonexistent')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No users found matching')

    def test_search_case_insensitive(self):
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard') + '?search=JOHN')
        self.assertContains(resp, 'john_doe')

    def test_search_returns_ticket_titles_for_admin(self):
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard') + '?search=Alpha')
        self.assertContains(resp, 'Alpha Issue')
        self.assertNotContains(resp, 'Beta Problem')

    def test_search_scopes_tickets_for_regular_user(self):
        # viewer1 should only see their own ticket results
        self.login_as(self.viewer1)
        resp = self.client.get(reverse('dashboard') + '?search=Issue')
        self.assertContains(resp, 'Alpha Issue')
        self.assertNotContains(resp, 'Beta Problem')

    def test_dashboard_without_search_shows_all_accessible_users(self):
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard'))
        self.assertContains(resp, 'john_doe')
        self.assertContains(resp, 'alice_smith')


class DashboardFilterTests(TestCase):
    """Test multi-filter functionality (Department, Role, Project)"""

    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        # create department records so we can assign FKs
        from accounts.models import Department
        # departments may already exist due to migration population
        self.dept_it, _ = Department.objects.get_or_create(name='IT')
        self.dept_dev, _ = Department.objects.get_or_create(name='DEVELOPER')

        # Create viewers with different departments
        self.it_viewer = User.objects.create(
            username='it_user', email='it@test.com', password='pass', 
            role='VIEWER', department=self.dept_it
        )
        self.it_viewer.created_by_admin = False
        self.it_viewer.save()
        
        self.dev_viewer = User.objects.create(
            username='dev_user', email='dev@test.com', password='pass', 
            role='VIEWER', department=self.dept_dev
        )
        self.dev_viewer.created_by_admin = False
        self.dev_viewer.save()
        
        # Create a manager with IT department
        self.it_manager = User.objects.create(
            username='it_manager', email='mgr@test.com', password='pass', 
            role='MANAGER', department=self.dept_it
        )
        self.it_manager.created_by_admin = True
        self.it_manager.save()
        
        # Create tickets
        from tickets.models import Ticket
        
        self.ticket_it_alpha = Ticket.objects.create(
            title='IT Alpha', description='IT alpha project', 
            department=self.dept_it, project_name='Alpha'
        )
        self.ticket_it_alpha.assignee = self.it_viewer
        self.ticket_it_alpha.save()
        
        self.ticket_it_beta = Ticket.objects.create(
            title='IT Beta', description='IT beta project', 
            department=self.dept_it, project_name='Beta'
        )
        self.ticket_it_beta.assignee = self.it_manager
        self.ticket_it_beta.save()
        
        self.ticket_dev_alpha = Ticket.objects.create(
            title='Dev Alpha', description='Dev alpha project', 
            department=self.dept_dev, project_name='Alpha'
        )
        self.ticket_dev_alpha.assignee = self.dev_viewer
        self.ticket_dev_alpha.save()
    
    def login_as(self, user):
        self.client.force_login(user)
    
    def test_filter_by_department_only(self):
        """Filter users by IT department"""
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard') + '?department=IT')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'it_user')
        self.assertContains(resp, 'it_manager')
        self.assertNotContains(resp, 'dev_user')
    
    def test_filter_by_role_only(self):
        """Filter users by MANAGER role"""
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard') + '?role=MANAGER')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'it_manager')
        self.assertNotContains(resp, 'it_user')
        self.assertNotContains(resp, 'dev_user')
    
    def test_filter_by_project_only(self):
        """Filter users by project assignment"""
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard') + '?project=Alpha')
        self.assertEqual(resp.status_code, 200)
        # Should show it_user and dev_user (assigned to Alpha project tickets)
        self.assertContains(resp, 'it_user')
        self.assertContains(resp, 'dev_user')
        self.assertNotContains(resp, 'it_manager')
    
    def test_multi_filter_department_and_role(self):
        """Filter by IT department AND MANAGER role"""
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard') + '?department=IT&role=MANAGER')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'it_manager')
        self.assertNotContains(resp, 'it_user')
        self.assertNotContains(resp, 'dev_user')
    
    def test_multi_filter_department_and_project(self):
        """Filter by IT department AND Alpha project"""
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard') + '?department=IT&project=Alpha')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'it_user')
        self.assertNotContains(resp, 'it_manager')  # Assigned to Beta, not Alpha
        self.assertNotContains(resp, 'dev_user')
    
    def test_multi_filter_all_three(self):
        """Filter by department, role, AND project simultaneously"""
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard') + '?department=IT&role=MANAGER&project=Beta')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'it_manager')
        self.assertNotContains(resp, 'it_user')
        self.assertNotContains(resp, 'dev_user')
    
    def test_filter_context_includes_available_options(self):
        """Verify context includes available departments, roles, and projects"""
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        # Check context lists available options
        self.assertIn('available_departments', resp.context)
        self.assertIn('available_roles', resp.context)
        self.assertIn('available_projects', resp.context)
        self.assertIn('IT', resp.context['available_departments'])
        self.assertIn('DEVELOPER', resp.context['available_departments'])
        self.assertIn('MANAGER', resp.context['available_roles'])
        self.assertIn('VIEWER', resp.context['available_roles'])
        self.assertIn('Alpha', resp.context['available_projects'])
    
    def test_filter_cleared_when_visiting_dashboard_without_params(self):
        """Filters should be empty strings when no params provided"""
        self.login_as(self.admin)
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['filter_department'], '')
        self.assertEqual(resp.context['filter_role'], '')
        self.assertEqual(resp.context['filter_project'], '')

