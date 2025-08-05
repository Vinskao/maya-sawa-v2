#
## 生成 Django Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 驗證設置

```bash
# 檢查 Django 配置
poetry run python manage.py check

# 檢查環境變量
poetry run python manage.py shell -c "from django.conf import settings; print('DATABASE_URL:', settings.DATABASES['default']['NAME']); print('REDIS_URL:', settings.REDIS_URL)"
```
