# Tickets App - Complete Documentation

## Overview
A fully functional Django Ticket Management System with Role-Based Access Control (RBAC) has been created and integrated into your RBAC project.

## Features Implemented

### 1. **Models**

#### Ticket Model
- **Fields:**
  - `id` (AutoField) - Primary key
  - `title` (CharField) - Ticket title
  - `assignee` (ForeignKey to User) - User assigned to the ticket
  - `assigned_to` (ForeignKey to User) - Admin/Manager who created the ticket
  - `description` (TextField) - Detailed description
  - `priority` (CharField) - Choices: LOW, MID, HIGH, CRITICAL (default: MID)
  - `status` (CharField) - Choices: OPEN, IN_PROGRESS, RESOLVED, CLOSED (default: OPEN)
  - `department` (CharField) - Department name
  - `project_name` (CharField) - Project name
  - `created_at` (DateTimeField) - Auto-set timestamp
  - `updated_at` (DateTimeField) - Auto-updated timestamp

#### Attachment Model
- **Fields:**
  - `ticket` (ForeignKey) - Related ticket
  - `file` (FileField) - Uploaded file
  - `uploaded_at` (DateTimeField) - Upload timestamp
  - `uploaded_by` (ForeignKey to User) - User who uploaded
- **Related name:** `attachments` on Ticket

#### ActivityTimeline Model
- **Fields:**
  - `ticket` (ForeignKey) - Related ticket
  - `user` (ForeignKey to User) - User who performed the action
  - `activity_type` (CharField) - Choices: STATUS_CHANGE, COMMENT, REASSIGN, ATTACHMENT_ADDED, PRIORITY_CHANGE
  - `status_change_log` (CharField) - Description of what changed
  - `comment` (TextField) - Comment text
  - `timestamp` (DateTimeField) - When action occurred
- **Related name:** `activity_timeline` on Ticket

---

## RBAC Permissions System

### Admin (is_superuser=True or role='ADMIN')
✅ Full access to all tickets
✅ Can create, read, update, delete any ticket
✅ Can reassign any ticket
✅ Can comment and add attachments to any ticket

### Manager (role='MANAGER')
✅ Can create new tickets
✅ Can read all tickets
✅ Can update any ticket
✅ Can delete any ticket (soft delete recommended in production)
✅ Can reassign any ticket
✅ Can comment and add attachments to any ticket

### Regular User (role='VIEWER' or any other role)
✅ Can view only tickets assigned to them
✅ Can update (status, description) tickets assigned to them
✅ Can reassign tickets assigned to them
✅ Can comment on tickets assigned to them
✅ Can add attachments to tickets assigned to them
❌ Cannot create tickets
❌ Cannot delete tickets
❌ Cannot view other users' tickets

---

## Views (Class-Based Views)

### TicketListView (ListView)
- **URL:** `/tickets/`
- **Template:** `tickets/ticket_list.html`
- Lists all tickets (filtered by user role)
- Managers/Admins see all tickets
- Regular users see only assigned tickets
- **Search bar:** users can search by title, description, project or department; results are scoped to their accessible tickets. Search term is passed via `?q=` query parameter and preserved across navigation.
- Pagination: 10 items per page (search query preserved between pages)

### TicketDetailView (DetailView)
- **URL:** `/tickets/<id>/`
- **Template:** `tickets/ticket_detail.html`
- Display ticket details with activity timeline and attachments
- Shows permission buttons based on user role
- Permission check: Only assigned user, manager, or admin can view

### TicketCreateView (CreateView)
- **URL:** `/tickets/create/`
- **Template:** `tickets/ticket_form.html`
- Allowed: Admin, Manager only
- Auto-logs creation in ActivityTimeline
- Redirects to ticket list on success

### TicketUpdateView (UpdateView)
- **URL:** `/tickets/<id>/update/`
- **Template:** `tickets/ticket_form.html`
- Managers can update any ticket
- Users can only update assigned tickets
- Auto-logs status and priority changes

### TicketDeleteView (DeleteView)
- **URL:** `/tickets/<id>/delete/`
- **Template:** `tickets/ticket_confirm_delete.html`
- Allowed: Admin only
- Confirmation page before deletion

### TicketReassignView (UpdateView)
- **URL:** `/tickets/<id>/reassign/`
- **Template:** `tickets/ticket_reassign.html`
- Managers can reassign any ticket
- Users can reassign their own tickets
- Auto-logs reassignment action

### AddCommentView
- **URL:** `/tickets/<id>/comment/` (POST)
- Allowed: Assigned user, manager, admin
- Returns JSON response
- Logs comment in ActivityTimeline

### AddAttachmentView
- **URL:** `/tickets/<id>/attachment/` (POST)
- Allowed: Assigned user, manager, admin
- Accepts file uploads (form shown on ticket detail page when permission granted)
- Files stored in `ticket_attachments/YYYY/MM/DD/` under `MEDIA_ROOT`
- Logs attachment action in ActivityTimeline

> **Note:** `MEDIA_URL`/`MEDIA_ROOT` must be configured and the
> development server updated to serve media files; see `settings.py` and
> project `urls.py` additions for `static()` in debug mode.

---

## Permission System (`permissions.py`)

### Key Functions

#### `check_ticket_access(user, ticket, action)`
Returns `True` or `False` based on user permissions for specific actions:
- Actions: `view`, `create`, `update`, `delete`, `reassign`, `comment`
- Admin/Manager always return `True`
- Users only get `True` for allowed actions on assigned tickets

#### `check_ticket_access_or_deny(user, ticket, action)`
Wrapper function that raises `PermissionDenied` exception if access not allowed.

---

## Admin Interface

All models registered in Django admin:
- Ticket admin with list filters, search, and custom fieldsets
- Attachment admin showing ticket and uploader
- ActivityTimeline admin with activity type filtering

---

## Templates Created

1. **ticket_list.html** - Display all tickets (paginated table)
2. **ticket_detail.html** - Ticket detail view with timeline and comments
3. **ticket_form.html** - Create/Update ticket form
4. **ticket_reassign.html** - Reassign ticket form
5. **ticket_confirm_delete.html** - Delete confirmation page

All templates use TailwindCSS with conditional styling based on priority/status.

---

## Database Migrations

Migration file: `tickets/migrations/0001_initial.py`
- Creates Ticket, Attachment, and ActivityTimeline tables
- Establishes foreign key relationships with proper constraints
- Applied successfully ✅

---

## URL Configuration

**Main URLs** (`rbac_project/urls.py`):
```
path('tickets/', include('tickets.urls'))
```

**Tickets URLs** (`tickets/urls.py`):
```
/tickets/                    - List all tickets
/tickets/create/             - Create new ticket
/tickets/<id>/               - View ticket details
/tickets/<id>/update/        - Update ticket
/tickets/<id>/delete/        - Delete ticket
/tickets/<id>/reassign/      - Reassign ticket
/tickets/<id>/comment/       - Add comment (POST)
/tickets/<id>/attachment/    - Add attachment (POST)
```

---

## Installation & Setup

### 1. Application Already Registered
- Added `tickets` to `INSTALLED_APPS` in settings.py
- Main project URLs already configured to include tickets.urls

### 2. Migrations Already Applied
```bash
python manage.py makemigrations tickets
python manage.py migrate
```

### 3. Access the Tickets App
- Start development server: `python manage.py runserver`
- Navigate to: `http://127.0.0.1:8000/tickets/`
- Admin interface: `http://127.0.0.1:8000/admin/`

---

## Security Features

✅ **Permission Checking:** All views validate user permissions before allowing access
✅ **CSRF Protection:** All forms include {% csrf_token %}
✅ **Activity Logging:** All changes logged in ActivityTimeline
✅ **Role-Based Access:** Permissions based on user role
✅ **Related Name Usage:** Prevents ForeignKey name clashes with accounts app

---

## History Tracking (Activity Timeline)

Automatically logs:
- ✅ Ticket creation
- ✅ Status changes
- ✅ Priority changes
- ✅ Reassignments
- ✅ Comments added
- ✅ Attachments uploaded

Each activity includes:
- Who performed it (user)
- When it happened (timestamp)
- What changed (status_change_log/comment)
- Activity type

---

## File Structure

```
rbac_project/
├── tickets/
│   ├── admin.py              (✅ Configured)
│   ├── apps.py               (✅ Configured)
│   ├── models.py             (✅ All models)
│   ├── views.py              (✅ All CBVs)
│   ├── urls.py               (✅ URL patterns)
│   ├── permissions.py        (✅ RBAC logic)
│   ├── migrations/
│   │   └── 0001_initial.py   (✅ Applied)
│   └── tests.py
├── Templates/tickets/
│   ├── ticket_list.html
│   ├── ticket_detail.html
│   ├── ticket_form.html
│   ├── ticket_reassign.html
│   └── ticket_confirm_delete.html
└── rbac_project/
    ├── settings.py           (✅ Updated with 'tickets')
    └── urls.py               (✅ Updated with tickets.urls)
```

---

## Note on Related Names

All ForeignKey relationships use explicit `related_name` to avoid conflicts:
- `Ticket.assignee` → related_name: `tickets_assigned_to_me`
- `Ticket.assigned_to` → related_name: `tickets_created_by_me`
- `Attachment.uploaded_by` → related_name: `ticket_attachments`
- `ActivityTimeline.user` → related_name: `ticket_activities`

---

## Testing Recommendations

1. Create a Manager user and verify they can create/edit all tickets
2. Create a regular user and verify they can only see assigned tickets
3. Test reassignment and verify activity log updates
4. Test file uploads and verify they're in correct directory
5. Admin should be able to perform all operations

---

**✅ Setup Complete! Your tickets app is ready to use.**
