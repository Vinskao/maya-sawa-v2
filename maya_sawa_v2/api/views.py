from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from maya_sawa_v2.conversations.models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer, CreateMessageSerializer


class ConversationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """發送訊息並觸發 AI 處理"""
        conversation = self.get_object()

        serializer = CreateMessageSerializer(
            data=request.data,
            context={'conversation': conversation}
        )

        if serializer.is_valid():
            message = serializer.save()
            return Response({
                'message': 'Message sent successfully',
                'message_id': message.id
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """獲取對話的所有訊息"""
        conversation = self.get_object()
        messages = conversation.messages.all()
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
