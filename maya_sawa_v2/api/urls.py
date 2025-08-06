from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, AIModelViewSet

conversation_router = DefaultRouter()
conversation_router.register(r'conversations', ConversationViewSet, basename='conversation')

ai_model_router = DefaultRouter()
ai_model_router.register(r'ai-models', AIModelViewSet, basename='ai-model')

urlpatterns = [
    path('maya-v2/', include(conversation_router.urls)),
    path('maya-v2/', include(ai_model_router.urls)),
]
