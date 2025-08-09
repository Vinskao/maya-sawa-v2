from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from maya_sawa_v2.conversations.models import Conversation, Message
from maya_sawa_v2.ai_processing.models import AIModel
from maya_sawa_v2.ai_processing.utils import AIProviderConfig, ModelNameMapper
from maya_sawa_v2.ai_processing.tasks import process_ai_response_sync
from maya_sawa_v2.ai_processing.km_sources.manager import KMSourceManager
from .serializers import ConversationSerializer, MessageSerializer, CreateMessageSerializer, AIModelSerializer, AIProviderConfigSerializer
from .permissions import AllowAnyPermission
import uuid
import logging

logger = logging.getLogger(__name__)


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


@api_view(['POST'])
@permission_classes([AllowAny])
def ask_with_model(request):
    """
    使用指定語言模型進行對話，並整合知識庫

    參數:
    - question: 問題內容
    - model_name: 語言模型名稱 (例如: gpt-4.1-nano, gpt-4o-mini)
    - sync: 是否同步處理 (預設: true)
    - use_knowledge_base: 是否使用知識庫 (預設: true)
    """
    try:
        question = request.data.get('question')
        model_name = request.data.get('model_name', 'gpt-4o-mini')
        sync = request.data.get('sync', True)
        use_knowledge_base = request.data.get('use_knowledge_base', True)

        if not question:
            return Response({'error': '問題內容不能為空'}, status=status.HTTP_400_BAD_REQUEST)

        # 獲取指定的 AI 模型
        try:
            # 先嘗試通過名稱查找
            ai_model = AIModel.objects.get(name__icontains=model_name, is_active=True)
        except AIModel.DoesNotExist:
            try:
                # 再嘗試通過 model_id 查找
                ai_model = AIModel.objects.get(model_id__icontains=model_name, is_active=True)
            except AIModel.DoesNotExist:
                # 如果都找不到，返回所有可用模型的信息
                available_models = AIModel.objects.filter(is_active=True).values('name', 'model_id', 'provider')
                return Response({
                    'error': f'找不到指定的模型: {model_name}',
                    'available_models': list(available_models)
                }, status=status.HTTP_400_BAD_REQUEST)

        # 創建會話和用戶訊息
        with transaction.atomic():
            # 生成唯一的 session_id
            session_id = f"qa-{uuid.uuid4().hex[:8]}"

            # 創建會話
            conversation = Conversation.objects.create(
                user_id=1,  # 預設用戶
                session_id=session_id,
                conversation_type='general',
                title=f"QA-{session_id}"
            )

            # 創建用戶訊息
            user_message = Message.objects.create(
                conversation=conversation,
                message_type='user',
                content=question
            )

                # 如果使用知識庫，先搜索相關知識
        knowledge_context = ""
        knowledge_citations = []
        if use_knowledge_base:
            try:
                from maya_sawa_v2.ai_processing.km_sources.manager import KMSourceManager
                from maya_sawa_v2.ai_processing.km_sources.base import KMQuery

                # 創建查詢對象（需要 user_id 與 conversation_id）
                query = KMQuery(
                    query=question,
                    user_id=conversation.user_id,
                    conversation_id=str(conversation.id),
                    domain='programming',  # 可根據實際分類結果覆蓋
                    metadata={
                        'km_source': 'programming_km',
                        'session_id': conversation.session_id
                    }
                )

                km_manager = KMSourceManager()
                logger.info(f"知識庫管理器初始化完成，可用源: {km_manager.list_sources()}")

                km_results = km_manager.search_all_suitable(query)
                logger.info(f"知識庫搜索完成，找到 {len(km_results)} 個結果")

                # 僅展示 Paprika 文章做為引用，且來源連結固定為 work URL
                paprika_results = [r for r in km_results if (r.metadata or {}).get('source_type') == 'paprika_api']
                if paprika_results:
                    knowledge_context = "\n\n相關知識庫內容：\n"
                    for i, result in enumerate(paprika_results[:3]):  # 只取前3個結果
                        meta = (result.metadata or {})
                        title = meta.get('title') or '參考文章'
                        file_path = meta.get('file_path') or ''
                        work_url = f"https://peoplesystem.tatdvsonorth.com/work/{file_path}" if file_path else "https://peoplesystem.tatdvsonorth.com/work/"
                        knowledge_context += f"{i+1}. {title} ({file_path})\n{result.content[:200]}...\n"

                        # 準備引用資訊（寫死為 work URL）
                        knowledge_citations.append({
                            'article_id': meta.get('article_id'),
                            'title': title,
                            'file_path': file_path,
                            'file_date': meta.get('file_date'),
                            'source': result.source,
                            'source_url': work_url,
                            'provider': meta.get('provider') or 'Paprika'
                        })

                    logger.info(f"找到 {len(km_results)} 個知識庫結果")
                else:
                    logger.info("未找到相關的知識庫內容")

            except Exception as e:
                logger.error(f"知識庫搜索失敗: {str(e)}")

        # 處理 AI 回應
        if sync:
            try:
                # 同步處理
                response = process_ai_response_sync(user_message, ai_model, knowledge_context=knowledge_context)

                # 如果有知識庫內容，將其添加到回應中
                if knowledge_context:
                    response = f"{response}\n\n{knowledge_context}"

                return Response({
                    'session_id': f"qa-{uuid.uuid4().hex[:8]}",
                    'conversation_id': str(conversation.id),
                    'question': question,
                    'ai_model': {
                        'id': ai_model.id,
                        'name': ai_model.name,
                        'provider': ai_model.provider
                    },
                    'status': 'completed',
                    'ai_response': response,
                    'knowledge_used': bool(knowledge_context),
                    'knowledge_citations': knowledge_citations,
                    'message': 'AI回复已完成'
                })

            except Exception as e:
                logger.error(f"AI 處理失敗: {str(e)}")
                return Response({
                    'error': f'AI 處理失敗: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # 目前暫不支援異步處理，避免未建立 ProcessingTask 導致錯誤
            return Response({
                'error': '目前僅支援同步處理，請將 sync 設為 true',
                'conversation_id': str(conversation.id),
                'question': question,
                'ai_model': {
                    'id': ai_model.id,
                    'name': ai_model.name,
                    'provider': ai_model.provider
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"API 錯誤: {str(e)}")
        return Response({
            'error': f'服務器錯誤: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def available_models(request):
    """獲取可用的語言模型列表"""
    try:
        models = AIModel.objects.filter(is_active=True).values('id', 'name', 'provider', 'model_id', 'is_active')
        return Response({
            'models': list(models)
        })
    except Exception as e:
        return Response({
            'error': f'獲取模型列表失敗: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def add_model(request):
    """手動添加 AI 模型"""
    try:
        from maya_sawa_v2.ai_processing.models import AIModel

        # 添加 GPT-4.1-nano 模型
        model_data = {
            'name': 'GPT-4.1 Nano',
            'provider': 'openai',
            'model_id': 'gpt-4.1-nano',
            'is_active': True,
            'config': {
                'model': 'gpt-4.1-nano',
                'max_tokens': 1000,
                'temperature': 0.7
            }
        }

        model, created = AIModel.objects.get_or_create(
            name=model_data['name'],
            defaults=model_data
        )

        if created:
            return Response({
                'message': f'成功創建模型: {model.name}',
                'model': {
                    'id': model.id,
                    'name': model.name,
                    'provider': model.provider,
                    'model_id': model.model_id,
                    'is_active': model.is_active
                }
            })
        else:
            # 更新現有模型
            for key, value in model_data.items():
                if key != 'name':
                    setattr(model, key, value)
            model.save()

            return Response({
                'message': f'成功更新模型: {model.name}',
                'model': {
                    'id': model.id,
                    'name': model.name,
                    'provider': model.provider,
                    'model_id': model.model_id,
                    'is_active': model.is_active
                }
            })

    except Exception as e:
        return Response({
            'error': f'添加模型失敗: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
