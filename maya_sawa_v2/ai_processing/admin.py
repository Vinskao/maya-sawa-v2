from django.contrib import admin
from .models import AIModel, ProcessingTask


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'model_id', 'is_active', 'created_at']
    list_filter = ['provider', 'is_active', 'created_at']
    search_fields = ['name', 'provider', 'model_id']
    readonly_fields = ['created_at']


@admin.register(ProcessingTask)
class ProcessingTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'ai_model', 'status', 'processing_time', 'created_at']
    list_filter = ['status', 'ai_model', 'created_at']
    search_fields = ['conversation__session_id', 'result', 'error_message']
    readonly_fields = ['created_at', 'completed_at']

    def processing_time_display(self, obj):
        if obj.processing_time:
            return f"{obj.processing_time:.2f}s"
        return "-"
    processing_time_display.short_description = 'Processing Time'
