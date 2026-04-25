from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile, shutil

from accounts.models import User, Department
from .models import Ticket, Attachment


class AttachmentTests(TestCase):
    def setUp(self):
        # use a temporary directory for media files during tests
        self.tmp_media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.tmp_media)
        self.override.enable()

        self.admin = User.objects.create_superuser('admin', 'a@a.com', 'pass')
        # Get or create a department for the ticket
        self.dept, _ = Department.objects.get_or_create(name='IT', defaults={'description': 'Information Technology'})
        self.ticket = Ticket.objects.create(
            title='Bug', description='something broke',
            department=self.dept, project_name='TestProject'
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.tmp_media)

    def login_as(self, user):
        self.client.force_login(user)

    def test_admin_can_upload_attachment(self):
        self.login_as(self.admin)
        url = reverse('add-attachment', args=[self.ticket.id])
        upload = SimpleUploadedFile('screenshot.png', b'fakeimage', content_type='image/png')
        resp = self.client.post(url, {'file': upload}, follow=True)
        self.assertRedirects(resp, reverse('ticket-detail', args=[self.ticket.id]))
        self.assertContains(resp, 'Attachment uploaded successfully.')
        self.assertTrue(Attachment.objects.filter(ticket=self.ticket).exists())
        att = Attachment.objects.get(ticket=self.ticket)
        self.assertIn('screenshot.png', att.file.name)

    def test_user_without_permission_cannot_upload(self):
        user = User.objects.create(username='viewer', password='pass', role='VIEWER')
        self.login_as(user)
        url = reverse('add-attachment', args=[self.ticket.id])
        fileobj = SimpleUploadedFile('test.txt', b'hello world')
        resp = self.client.post(url, {'file': fileobj})
        self.assertEqual(resp.status_code, 403)


class TicketListSearchTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin2', 'a2@a.com', 'pass')
        self.manager = User.objects.create(username='mgr', password='pass', role='MANAGER')
        self.user1 = User.objects.create(username='user1', password='pass', role='VIEWER')
        self.user2 = User.objects.create(username='user2', password='pass', role='VIEWER')
        
        # Get or create departments
        self.it_dept, _ = Department.objects.get_or_create(name='IT', defaults={'description': 'Information Technology'})
        self.hr_dept, _ = Department.objects.get_or_create(name='HR', defaults={'description': 'Human Resources'})
        
        # Tickets for search
        self.ticket_a = Ticket.objects.create(
            title='Alpha issue', description='something about alpha', department=self.it_dept, project_name='Alpha')
        self.ticket_b = Ticket.objects.create(
            title='Beta problem', description='beta description', department=self.hr_dept, project_name='Beta')
        # assign to user1 and user2
        self.ticket_a.assignee = self.user1
        self.ticket_a.save()
        self.ticket_b.assignee = self.user2
        self.ticket_b.save()

    def login_as(self, user):
        self.client.force_login(user)

    def test_admin_sees_all_tickets_and_can_search(self):
        self.login_as(self.admin)
        url = reverse('ticket-list')
        resp = self.client.get(url, {'q': 'Alpha'})
        self.assertContains(resp, 'Alpha issue')
        self.assertNotContains(resp, 'Beta problem')
        # search by description
        resp = self.client.get(url, {'q': 'beta'})
        self.assertContains(resp, 'Beta problem')
        self.assertNotContains(resp, 'Alpha issue')

    def test_regular_user_can_view_all_tickets(self):
        self.login_as(self.user1)
        url = reverse('ticket-list')
        # user1 should now see all tickets (Alpha and Beta)
        resp = self.client.get(url)
        self.assertContains(resp, 'Alpha issue')
        self.assertContains(resp, 'Beta problem')
        # search for Beta ticket should work even though user1 is not assigned to it
        resp = self.client.get(url, {'q': 'Beta'})
        self.assertContains(resp, 'Beta problem')
        # search for own ticket still works
        resp = self.client.get(url, {'q': 'Alpha'})
        self.assertContains(resp, 'Alpha issue')


class TicketPermissionsTests(TestCase):
    """Test ticket CRUD permissions for different user roles"""
    
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        self.manager = User.objects.create(username='manager', password='pass', role='MANAGER')
        self.editor = User.objects.create(username='editor', password='pass', role='EDITOR')
        self.hybrid = User.objects.create(username='hybrid', password='pass', role='HYBRID')
        self.viewer = User.objects.create(username='viewer', password='pass', role='VIEWER')
        
        # Get or create departments
        self.it_dept, _ = Department.objects.get_or_create(name='IT', defaults={'description': 'Information Technology'})
        self.hr_dept, _ = Department.objects.get_or_create(name='HR', defaults={'description': 'Human Resources'})
        
        # Create tickets assigned to different users
        self.admin_ticket = Ticket.objects.create(
            title='Admin Ticket', description='Created by admin',
            department=self.it_dept, project_name='AdminProject'
        )
        self.admin_ticket.assignee = self.admin
        self.admin_ticket.save()
        
        self.manager_ticket = Ticket.objects.create(
            title='Manager Ticket', description='For manager',
            department=self.it_dept, project_name='ManagerProject'
        )
        self.manager_ticket.assignee = self.manager
        self.manager_ticket.save()
        
        self.viewer_ticket = Ticket.objects.create(
            title='Viewer Ticket', description='For viewer',
            department=self.hr_dept, project_name='ViewerProject'
        )
        self.viewer_ticket.assignee = self.viewer
        self.viewer_ticket.save()
        
        self.unassigned_ticket = Ticket.objects.create(
            title='Unassigned Ticket', description='No assignee',
            department=self.it_dept, project_name='CommonProject'
        )
    
    def login_as(self, user):
        self.client.force_login(user)
    
    def test_admin_can_view_all_tickets(self):
        """Admin should view all tickets"""
        self.login_as(self.admin)
        resp = self.client.get(reverse('ticket-list'))
        self.assertContains(resp, 'Admin Ticket')
        self.assertContains(resp, 'Manager Ticket')
        self.assertContains(resp, 'Viewer Ticket')
        self.assertContains(resp, 'Unassigned Ticket')
    
    def test_manager_can_view_all_tickets(self):
        """Manager should view all tickets"""
        self.login_as(self.manager)
        resp = self.client.get(reverse('ticket-list'))
        self.assertContains(resp, 'Admin Ticket')
        self.assertContains(resp, 'Manager Ticket')
        self.assertContains(resp, 'Viewer Ticket')
        self.assertContains(resp, 'Unassigned Ticket')
    
    def test_viewer_can_view_all_tickets(self):
        """Viewer should be able to view all tickets (including unassigned and others' tickets)"""
        self.login_as(self.viewer)
        resp = self.client.get(reverse('ticket-list'))
        self.assertContains(resp, 'Admin Ticket')
        self.assertContains(resp, 'Manager Ticket')
        self.assertContains(resp, 'Viewer Ticket')
        self.assertContains(resp, 'Unassigned Ticket')
    
    def test_viewer_can_view_ticket_detail_all(self):
        """Viewer should be able to view detail of any ticket"""
        self.login_as(self.viewer)
        resp = self.client.get(reverse('ticket-detail', args=[self.admin_ticket.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Admin Ticket')
    
    def test_admin_can_update_any_ticket(self):
        """Admin should be able to update any ticket"""
        self.login_as(self.admin)
        resp = self.client.get(reverse('ticket-update', args=[self.viewer_ticket.id]))
        self.assertEqual(resp.status_code, 200)
    
    def test_manager_can_update_any_ticket(self):
        """Manager should be able to update any ticket"""
        self.login_as(self.manager)
        resp = self.client.get(reverse('ticket-update', args=[self.viewer_ticket.id]))
        self.assertEqual(resp.status_code, 200)
    
    def test_assignee_can_update_own_ticket(self):
        """User assigned to a ticket should be able to update it"""
        self.login_as(self.viewer)
        resp = self.client.get(reverse('ticket-update', args=[self.viewer_ticket.id]))
        self.assertEqual(resp.status_code, 200)
    
    def test_non_assignee_cannot_update_others_ticket(self):
        """User not assigned to a ticket should NOT be able to update it"""
        self.login_as(self.viewer)
        resp = self.client.get(reverse('ticket-update', args=[self.admin_ticket.id]))
        self.assertEqual(resp.status_code, 403)
    
    def test_editor_cannot_update_unassigned_ticket(self):
        """Editor not assigned to a ticket should NOT be able to update it"""
        self.login_as(self.editor)
        resp = self.client.get(reverse('ticket-update', args=[self.unassigned_ticket.id]))
        self.assertEqual(resp.status_code, 403)
    
    def test_edit_button_visible_for_admin(self):
        """Edit button should be visible in ticket detail for admin"""
        self.login_as(self.admin)
        resp = self.client.get(reverse('ticket-detail', args=[self.viewer_ticket.id]))
        self.assertContains(resp, '✏️ Edit')
    
    def test_edit_button_visible_for_manager(self):
        """Edit button should be visible in ticket detail for manager"""
        self.login_as(self.manager)
        resp = self.client.get(reverse('ticket-detail', args=[self.viewer_ticket.id]))
        self.assertContains(resp, '✏️ Edit')
    
    def test_edit_button_visible_for_assignee(self):
        """Edit button should be visible for ticket assignee"""
        self.login_as(self.viewer)
        resp = self.client.get(reverse('ticket-detail', args=[self.viewer_ticket.id]))
        self.assertContains(resp, '✏️ Edit')
    
    def test_edit_button_not_visible_for_non_assignee(self):
        """Edit button should NOT be visible for non-admin/manager/non-assignee"""
        self.login_as(self.editor)
        resp = self.client.get(reverse('ticket-detail', args=[self.viewer_ticket.id]))
        self.assertNotContains(resp, '✏️ Edit')
    
    def test_delete_button_visible_for_admin_and_manager(self):
        """Delete button should be visible for admin and manager"""
        # Admin should see delete
        self.login_as(self.admin)
        resp = self.client.get(reverse('ticket-detail', args=[self.viewer_ticket.id]))
        self.assertContains(resp, '🗑️ Delete')
        
        # Manager should see delete
        self.login_as(self.manager)
        resp = self.client.get(reverse('ticket-detail', args=[self.viewer_ticket.id]))
        self.assertContains(resp, '🗑️ Delete')
        
        # Assignee should NOT see delete
        self.login_as(self.viewer)
        resp = self.client.get(reverse('ticket-detail', args=[self.viewer_ticket.id]))
        self.assertNotContains(resp, '🗑️ Delete')

