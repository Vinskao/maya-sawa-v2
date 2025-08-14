import time
import logging
from celery import shared_task
from .models import ProcessingTask
from maya_sawa_v2.ai_processing.services.ai_response_service import AIResponseService

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_ai_response(self, task_id):
    """處理 AI 回應的非同步任務"""
    try:
        processing_task = ProcessingTask.objects.get(id=task_id)
        processing_task.status = 'processing'
        processing_task.save(update_fields=['status'])

        service = AIResponseService()
        service.process_task(processing_task)

        logger.info(f"AI processing completed for task {task_id}")

    except Exception as e:
        logger.error(f"AI processing failed for task {task_id}: {str(e)}")
        processing_task.status = 'failed'
        processing_task.error_message = str(e)
        processing_task.save(update_fields=['status', 'error_message'])


def process_ai_response_sync(user_message, ai_model, knowledge_context: str | None = None):
    """同步处理AI回应，支持外部知識上下文"""
    try:
        service = AIResponseService()
        return service.process_sync(user_message=user_message, ai_model=ai_model, knowledge_context=knowledge_context)
    except Exception as e:
        # 保留原有錯誤紀錄行為
        import logging as _logging
        _logging.getLogger(__name__).error(
            f"AI processing failed for message {user_message.id}: {str(e)}"
        )
        raise e



