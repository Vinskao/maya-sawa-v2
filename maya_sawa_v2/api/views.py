from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from maya_sawa_v2.conversations.models import Conversation, Message
from maya_sawa_v2.ai_processing.models import AIModel
from maya_sawa_v2.ai_processing.utils import AIProviderConfig, ModelNameMapper
from .serializers import ConversationSerializer, MessageSerializer, CreateMessageSerializer, AIModelSerializer, AIProviderConfigSerializer
from .permissions import AllowAnyPermission
import uuid


class ConversationViewSet(viewsets.ModelViewSet):
    """
    对话管理视图集

    提供对话的CRUD操作，包括：
    - 创建、读取、更新、删除对话
    - 发送消息并触发AI处理
    - 获取对话消息历史
    - 获取可用的AI模型
    """
    permission_classes = [AllowAnyPermission]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        """获取对话列表 - 根据认证状态决定过滤条件"""
        if getattr(self.request, 'user', None) and self.request.user.is_authenticated:
            # 如果用户已认证，只返回该用户的对话
            return Conversation.objects.filter(user=self.request.user)
        else:
            # 如果未认证，返回所有对话（开发模式）
            return Conversation.objects.all()

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """
        发送消息并触发AI处理

        参数:
        - content: 消息内容
        - ai_model_id: 可选的AI模型ID

        返回:
        - message_id: 创建的消息ID
        """
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
        """
        获取对话的所有消息

        返回对话的完整消息历史，包括用户消息和AI回复
        """
        conversation = self.get_object()
        messages = conversation.messages.all()
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def available_models(self, request):
        """
        获取可用的AI模型列表

        返回所有启用的AI模型，包括模型名称、提供者等信息
        """
        models = AIModel.objects.filter(is_active=True)
        serializer = AIModelSerializer(models, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def ai_providers(self, request):
        """
        获取AI提供者配置

        返回所有AI提供者的配置信息，包括：
        - 提供者名称
        - 可用模型列表
        - 默认模型
        - 启用状态
        """
        providers_config = AIProviderConfig.get_all_providers_config()

        # 轉換為序列化器格式
        providers_data = []
        for provider, config in providers_config.items():
            providers_data.append({
                'provider': provider,
                'display_name': ModelNameMapper.get_provider_display_name(provider),
                'models': config['models'],
                'available_models': config['available_models'],
                'default_model': config['default_model'],
                'enabled': config['enabled']
            })

        serializer = AIProviderConfigSerializer(providers_data, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def ask(self, request):
        """
        直接问答API - 支持指定AI模型

        查询参数:
        - question: 问题内容
        - model: AI模型ID或模型名称 (可选，默认使用第一个可用模型)
        - session_id: 会话ID (可选，如果不提供会创建新会话)
        - sync: 是否同步处理 (可选，默认为false，使用异步处理)

        示例:
        GET /maya-v2/conversations/ask/?question=Java如何实现多线程&model=gpt-4o-mini&sync=true
        """
        question = request.query_params.get('question')
        model_param = request.query_params.get('model')
        session_id = request.query_params.get('session_id', f'qa-{uuid.uuid4().hex[:8]}')
        sync_mode = request.query_params.get('sync', 'false').lower() == 'true'

        if not question:
            return Response({
                'error': '问题参数是必需的'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 获取或创建用户（为未认证用户提供默认用户）
        if request.user.is_authenticated:
            user = request.user
        else:
            # 为未认证用户使用默认用户
            from maya_sawa_v2.users.models import User
            user, created = User.objects.get_or_create(
                username='anonymous_user',
                defaults={
                    'email': 'anonymous@example.com',
                    'is_active': True
                }
            )

        # 获取或创建会话
        conversation, created = Conversation.objects.get_or_create(
            session_id=session_id,
            defaults={
                'user': user,
                'title': f'问答会话 - {question[:50]}...',
                'conversation_type': 'knowledge_query'
            }
        )

        # 确定使用的AI模型
        ai_model = None
        if model_param:
            # 尝试通过ID查找
            try:
                ai_model = AIModel.objects.get(id=model_param, is_active=True)
            except (ValueError, AIModel.DoesNotExist):
                # 尝试通过模型名称查找
                try:
                    ai_model = AIModel.objects.get(model_id=model_param, is_active=True)
                except AIModel.DoesNotExist:
                    return Response({
                        'error': f'指定的模型 "{model_param}" 不存在或未启用'
                    }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # 使用默认模型
            ai_model = AIModel.objects.filter(is_active=True).first()

        if not ai_model:
            return Response({
                'error': '没有可用的AI模型'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 创建用户消息
        user_message = Message.objects.create(
            conversation=conversation,
            message_type='user',
            content=question
        )

        if sync_mode:
            # 同步处理 - 直接调用AI
            try:
                from maya_sawa_v2.ai_processing.tasks import process_ai_response_sync
                ai_response = process_ai_response_sync(user_message, ai_model)
                
                return Response({
                    'session_id': session_id,
                    'conversation_id': str(conversation.id),
                    'question': question,
                    'ai_model': {
                        'id': ai_model.id,
                        'name': ai_model.name,
                        'provider': ai_model.provider
                    },
                    'status': 'completed',
                    'ai_response': ai_response,
                    'message': 'AI回复已完成'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    'error': f'AI处理失败: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # 异步处理
            from maya_sawa_v2.ai_processing.tasks import process_ai_response
            from maya_sawa_v2.ai_processing.models import ProcessingTask

            task = ProcessingTask.objects.create(
                conversation=conversation,
                message=user_message,
                ai_model=ai_model
            )

            # 异步处理AI回复
            process_ai_response.delay(task.id)

            return Response({
                'session_id': session_id,
                'conversation_id': str(conversation.id),
                'question': question,
                'ai_model': {
                    'id': ai_model.id,
                    'name': ai_model.name,
                    'provider': ai_model.provider
                },
                'task_id': task.id,
                'status': 'processing',
                'message': '问题已提交，AI正在处理中...'
            }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'])
    def task_status(self, request):
        """
        查看任务处理状态

        查询参数:
        - task_id: 任务ID

        示例:
        GET /maya-v2/conversations/task_status/?task_id=1
        """
        task_id = request.query_params.get('task_id')
        
        if not task_id:
            return Response({
                'error': '任务ID参数是必需的'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            from maya_sawa_v2.ai_processing.models import ProcessingTask
            task = ProcessingTask.objects.get(id=task_id)
            
            # 获取最新的AI消息
            ai_message = None
            if task.status == 'completed':
                ai_message = task.conversation.messages.filter(
                    message_type='ai',
                    created_at__gte=task.completed_at
                ).first()

            return Response({
                'task_id': task.id,
                'status': task.status,
                'processing_time': task.processing_time,
                'completed_at': task.completed_at,
                'error_message': task.error_message,
                'ai_response': ai_message.content if ai_message else None,
                'conversation_id': str(task.conversation.id)
            })

        except ProcessingTask.DoesNotExist:
            return Response({
                'error': f'任务 {task_id} 不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'查询任务状态时发生错误: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIModelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    AI模型视图集

    提供AI模型的只读操作，包括：
    - 获取所有AI模型列表
    - 获取单个AI模型详情
    - 支持包含/排除不可用模型的查询参数
    """
    permission_classes = [AllowAnyPermission]
    serializer_class = AIModelSerializer

    def get_queryset(self):
        """
        根据查询参数决定是否包含不可用的模型

        查询参数:
        - include_inactive: 是否包含不可用的模型 (true/false)
        """
        include_inactive = self.request.query_params.get('include_inactive', 'false').lower() == 'true'
        if include_inactive:
            return AIModel.objects.all()
        else:
            return AIModel.objects.filter(is_active=True)
