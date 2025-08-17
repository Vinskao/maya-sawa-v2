from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConversationViewSet,
    AIModelViewSet,
    ask_with_model,
    available_models,
    add_model,
    chat_history,
    legacy_chat_history,
)

conversation_router = DefaultRouter()
conversation_router.register(r'conversations', ConversationViewSet, basename='conversation')

ai_model_router = DefaultRouter()
ai_model_router.register(r'ai-models', AIModelViewSet, basename='ai-model')

urlpatterns = [
    path('maya-v2/', include(conversation_router.urls)),
    path('maya-v2/', include(ai_model_router.urls)),
    path('maya-v2/ask-with-model/', ask_with_model, name='ask_with_model'),
    path('maya-v2/available-models/', available_models, name='available_models'),
    path('maya-v2/add-model/', add_model, name='add_model'),
    # Chat history endpoints
    path('maya-v2/qa/chat-history/<str:session_id>', chat_history, name='chat_history'),
    # Legacy compatibility: /maya-sawa/qa/chat-history/<tail>
    path('maya-sawa/qa/chat-history/<str:session_tail>', legacy_chat_history, name='legacy_chat_history'),
]
