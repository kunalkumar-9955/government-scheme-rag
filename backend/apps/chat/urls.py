from django.urls import path
from .views import ConversationListCreateView, ConversationDetailView, SendMessageView, MessageFeedbackView

urlpatterns = [
    path("conversations/", ConversationListCreateView.as_view(), name="conversation-list-create"),
    path("conversations/<uuid:conv_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("conversations/<uuid:conv_id>/messages/", SendMessageView.as_view(), name="send-message"),
    path("messages/<uuid:message_id>/feedback/", MessageFeedbackView.as_view(), name="message-feedback"),
]
