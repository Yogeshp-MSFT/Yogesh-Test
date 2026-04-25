from django.urls import path
from .views import (
    TicketListView,
    TicketDetailView,
    TicketCreateView,
    TicketUpdateView,
    TicketDeleteView,
    TicketReassignView,
    AddCommentView,
    AddAttachmentView,
)

urlpatterns = [
    path('', TicketListView.as_view(), name='ticket-list'),
    path('create/', TicketCreateView.as_view(), name='ticket-create'),
    path('<int:pk>/', TicketDetailView.as_view(), name='ticket-detail'),
    path('<int:pk>/update/', TicketUpdateView.as_view(), name='ticket-update'),
    path('<int:pk>/delete/', TicketDeleteView.as_view(), name='ticket-delete'),
    path('<int:pk>/reassign/', TicketReassignView.as_view(), name='ticket-reassign'),
    path('<int:pk>/comment/', AddCommentView.as_view(), name='add-comment'),
    path('<int:pk>/attachment/', AddAttachmentView.as_view(), name='add-attachment'),
]
