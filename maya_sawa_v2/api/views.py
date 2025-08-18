from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from maya_sawa_v2.conversations.models import Conversation, Message
from maya_sawa_v2.ai_processing.models import AIModel
from maya_sawa_v2.ai_processing.utils import AIProviderConfig, ModelNameMapper
from maya_sawa_v2.ai_processing.tasks import process_ai_response_sync
from maya_sawa_v2.ai_processing.km_sources.manager import KMSourceManager
from .serializers import ConversationSerializer, MessageSerializer, CreateMessageSerializer, AIModelSerializer, AIProviderConfigSerializer
from .services import ChatHistoryService
from .permissions import AllowAnyPermission
import uuid
import logging

logger = logging.getLogger(__name__)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    對話管理視圖集

    提供對話的CRUD操作，包括：
    - 建立、讀取、更新、刪除對話
    - 發送訊息並觸發AI處理
    - 獲取對話訊息歷史
    - 獲取可用的AI模型
    """
    permission_classes = [AllowAnyPermission]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        """獲取對話列表 - 根據認證狀態決定過濾條件"""
        if getattr(self.request, 'user', None) and self.request.user.is_authenticated:
            # 如果用戶已認證，只返回該用戶的對話
            return Conversation.objects.filter(user=self.request.user)
        else:
            # 如果未認證，返回所有對話（開發模式）
            return Conversation.objects.all()

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """
        發送訊息並觸發AI處理

        參數:
        - content: 訊息內容
        - ai_model_id: 可選的AI模型ID

        返回:
        - message_id: 建立的訊息ID
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
        獲取對話的所有訊息

        返回對話的完整訊息歷史，包括用戶訊息和AI回覆
        """
        conversation = self.get_object()
        messages = conversation.messages.all()
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def available_models(self, request):
        """
        獲取可用的AI模型列表

        返回所有啟用的AI模型，包括模型名稱、提供者等資訊
        """
        models = AIModel.objects.filter(is_active=True)
        serializer = AIModelSerializer(models, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def ai_providers(self, request):
        """
        獲取AI提供者配置

        返回所有AI提供者的配置資訊，包括：
        - 提供者名稱
        - 可用模型列表
        - 預設模型
        - 啟用狀態
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
        查看任務處理狀態

        查詢參數:
        - task_id: 任務ID

        範例:
        GET /maya-v2/conversations/task_status/?task_id=1
        """
        task_id = request.query_params.get('task_id')

        if not task_id:
            return Response({
                'error': '任務ID參數是必需的'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            from maya_sawa_v2.ai_processing.models import ProcessingTask
            task = ProcessingTask.objects.get(id=task_id)

            # 獲取最新的AI訊息
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
                'error': f'任務 {task_id} 不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'查詢任務狀態時發生錯誤: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIModelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    AI模型視圖集

    提供AI模型的只讀操作，包括：
    - 獲取所有AI模型列表
    - 獲取單個AI模型詳情
    - 支援包含/排除不可用模型的查詢參數
    """
    permission_classes = [AllowAnyPermission]
    serializer_class = AIModelSerializer

    def get_queryset(self):
        """
        根據查詢參數決定是否包含不可用的模型

        查詢參數:
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

        # 準備會話用戶（若無預設用戶，建立一個輕量帳號）
        UserModel = get_user_model()
        user = UserModel.objects.filter(id=1).first()
        if not user:
            user = UserModel.objects.filter(username='api_default').first()
        if not user:
            # 建立不可登入的預設用戶
            user = UserModel.objects.create_user(username=f"api_default")

        # 創建會話和用戶訊息
        with transaction.atomic():
            # 生成唯一的 session_id
            session_id = f"qa-{uuid.uuid4().hex[:8]}"

            # 創建會話
            conversation = Conversation.objects.create(
                user=user,
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

        # 寫入 Redis 聊天歷史
        try:
            ch = ChatHistoryService()
            ch.set_meta(session_id, {
                'user_id': str(user.id),
                'conversation_id': str(conversation.id),
                'created_at': str(int(timezone.now().timestamp()))
            })
            ch.append_message(session_id, 'user', question)
        except Exception as _:
            pass

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
                knowledge_found = False
                if paprika_results:
                    knowledge_context = "\n\n相關知識庫內容：\n"
                    knowledge_found = True
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
                    # 當沒有找到知識庫內容時，添加明確的說明
                    knowledge_context = "\n\n注意：無法從知識庫中找到相關的資訊來回答您的問題。以下回答基於我的訓練資料。"

            except Exception as e:
                logger.error(f"知識庫搜索失敗: {str(e)}")

        # 處理 AI 回應
        if sync:
            try:
                # 同步處理
                response = process_ai_response_sync(user_message, ai_model, knowledge_context=knowledge_context)

                # 如果有知識庫內容或沒有找到知識庫內容的說明，將其添加到回應中
                if knowledge_context:
                    response = f"{response}\n\n{knowledge_context}"

                # 寫入 Redis 聊天歷史（AI 回應）
                try:
                    ch = ChatHistoryService()
                    ch.append_message(session_id, 'assistant', response, {'model': ai_model.name})
                except Exception:
                    pass

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
                    'ai_response': response,
                    'knowledge_used': knowledge_found,
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
def chat_history(request, session_id: str):
    """取得聊天歷史（Redis）。"""
    try:
        ch = ChatHistoryService()
        data = {
            'session_id': session_id,
            'meta': ch.get_meta(session_id),
            'messages': ch.get_history(session_id),
        }
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'OPTIONS'])
@permission_classes([AllowAny])
def legacy_chat_history(request, session_tail: str):
    """相容舊路徑 /maya-sawa/qa/chat-history/{session_tail}。
    新制 session_id 以 qa- 開頭，這裡若未帶 prefix，將自動補上。
    """
    try:
        session_id = session_tail if session_tail.startswith('qa-') else f'qa-{session_tail}'
        ch = ChatHistoryService()
        data = {
            'session_id': session_id,
            'meta': ch.get_meta(session_id),
            'messages': ch.get_history(session_id),
        }
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
    """從環境變數批量添加/更新 AI 模型"""
    try:
        import os
        from maya_sawa_v2.ai_processing.models import AIModel

        # 獲取啟用的提供者
        enabled_providers = os.getenv('ENABLED_PROVIDERS', 'openai,mock').split(',')

        created_count = 0
        updated_count = 0
        models_info = []

        for provider in enabled_providers:
            provider = provider.strip().upper()

            # 獲取該提供者的所有模型
            models_key = f'{provider}_MODELS'
            available_models_key = f'{provider}_AVAILABLE_MODELS'
            default_model_key = f'{provider}_DEFAULT_MODEL'

            all_models = os.getenv(models_key, '').split(',')
            available_models = os.getenv(available_models_key, '').split(',')
            default_model = os.getenv(default_model_key, '')

            if not all_models or all_models == ['']:
                continue

            # 為每個模型創建記錄
            for model_id in all_models:
                model_id = model_id.strip()
                if not model_id:
                    continue

                # 檢查是否為可用模型
                is_available = model_id in available_models

                # 生成模型名稱
                model_name = _generate_model_name(provider, model_id)

                model_data = {
                    'name': model_name,
                    'provider': provider.lower(),
                    'model_id': model_id,
                    'is_active': is_available,
                    'config': {
                        'model': model_id,
                        'max_tokens': 1000,
                        'temperature': 0.7
                    }
                }

                model, created = AIModel.objects.get_or_create(
                    name=model_name,
                    defaults=model_data
                )

                if created:
                    created_count += 1
                    models_info.append({
                        'id': model.id,
                        'name': model.name,
                        'provider': model.provider,
                        'model_id': model.model_id,
                        'is_active': model.is_active,
                        'action': 'created'
                    })
                else:
                    # 更新現有模型
                    for key, value in model_data.items():
                        if key != 'name':  # 不更新名稱
                            setattr(model, key, value)
                    model.save()
                    updated_count += 1
                    models_info.append({
                        'id': model.id,
                        'name': model.name,
                        'provider': model.provider,
                        'model_id': model.model_id,
                        'is_active': model.is_active,
                        'action': 'updated'
                    })

        return Response({
            'message': f'AI 模型設置完成！創建: {created_count}, 更新: {updated_count}',
            'models': models_info
        })

    except Exception as e:
        return Response({
            'error': f'添加模型失敗: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _generate_model_name(provider, model_id):
    """生成模型顯示名稱"""
    name_mapping = {
        'OPENAI': {
            'gpt-4o-mini': 'GPT-4o Mini',
            'gpt-4o': 'GPT-4o',
            'gpt-4.1-nano': 'GPT-4.1 Nano',
            'gpt-3.5-turbo': 'GPT-3.5 Turbo'
        },
        'GEMINI': {
            'gemini-1.5-flash': 'Gemini 1.5 Flash',
            'gemini-1.5-pro': 'Gemini 1.5 Pro'
        },
        'QWEN': {
            'qwen-turbo': 'Qwen Turbo',
            'qwen-plus': 'Qwen Plus'
        }
    }

    return name_mapping.get(provider, {}).get(model_id, f'{provider} {model_id}')
