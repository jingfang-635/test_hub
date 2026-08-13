from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from .views import (
    UiProjectViewSet,
    UiProjectEnsureView,
    LocatorStrategyViewSet,
    ElementGroupViewSet,
    ElementViewSet,
    TestScriptViewSet,
    PageObjectViewSet,
    ScriptStepViewSet,
    TestSuiteViewSet,
    TestExecutionViewSet,
    ScreenshotViewSet,
    TestCaseViewSet,
    TestCaseStepViewSet,
    TestCaseExecutionViewSet,
    UiScheduledTaskViewSet,
    AIExecutionRecordViewSet,
    AICaseViewSet,
    UiNotificationLogViewSet,
    OperationRecordViewSet,
    UiDashboardViewSet
)
from .views_config import EnvironmentConfigViewSet, AIIntelligentModeConfigViewSet
from .views_exploration import AIExplorationTaskViewSet, AIExplorationStepViewSet
from .views_codegen import PlaywrightCodegenViewSet

router = DefaultRouter()
router.register(r'dashboard', UiDashboardViewSet, basename='dashboard')
router.register(r'projects', UiProjectViewSet)
router.register(r'locator-strategies', LocatorStrategyViewSet)
router.register(r'element-groups', ElementGroupViewSet)
router.register(r'elements', ElementViewSet)
router.register(r'test-scripts', TestScriptViewSet)
router.register(r'page-objects', PageObjectViewSet)
router.register(r'steps', ScriptStepViewSet)
router.register(r'test-suites', TestSuiteViewSet)
router.register(r'test-executions', TestExecutionViewSet)
router.register(r'screenshots', ScreenshotViewSet)
router.register(r'test-cases', TestCaseViewSet)
router.register(r'test-case-steps', TestCaseStepViewSet)
router.register(r'test-case-executions', TestCaseExecutionViewSet)
router.register(r'scheduled-tasks', UiScheduledTaskViewSet)
router.register(r'ai-execution-records', AIExecutionRecordViewSet)
router.register(r'ai-cases', AICaseViewSet, basename='ai-cases')
router.register(r'ai-case-generation', AICaseViewSet, basename='ai-case-generation')
router.register(r'notification-logs', UiNotificationLogViewSet)
router.register(r'operation-records', OperationRecordViewSet)
router.register(r'ai-exploration-tasks', AIExplorationTaskViewSet, basename='ai-exploration-tasks')
router.register(r'ai-exploration-steps', AIExplorationStepViewSet, basename='ai-exploration-steps')
router.register(r'codegen', PlaywrightCodegenViewSet, basename='playwright-codegen')


# Configuration Center APIs
router.register(r'config/environment', EnvironmentConfigViewSet, basename='config-environment')
router.register(r'config/ai-mode', AIIntelligentModeConfigViewSet, basename='config-ai-mode')
router.register(r'ai-models', AIIntelligentModeConfigViewSet, basename='ai-models')

# Pipeline 显式路由（优先于 router，避免仅依赖 @action 斜杠路径时旧进程未加载）
codegen_pipeline_parse = PlaywrightCodegenViewSet.as_view({'post': 'pipeline_parse'})
codegen_pipeline_to_case_steps = PlaywrightCodegenViewSet.as_view({'post': 'pipeline_to_case_steps'})
codegen_pipeline_detail = PlaywrightCodegenViewSet.as_view({'get': 'pipeline_detail'})
codegen_pipeline_generate_plan = PlaywrightCodegenViewSet.as_view({'post': 'pipeline_generate_plan'})
codegen_pipeline_update_plan = PlaywrightCodegenViewSet.as_view({
    'patch': 'pipeline_update_plan',
    'put': 'pipeline_update_plan',
})
codegen_pipeline_confirm_plan = PlaywrightCodegenViewSet.as_view({'post': 'pipeline_confirm_plan'})
codegen_pipeline_generate_scripts = PlaywrightCodegenViewSet.as_view({'post': 'pipeline_generate_scripts'})

urlpatterns = [
    # 独立 APIView，避免被 projects/<pk>/ 抢先匹配导致 POST ensure 405
    path('projects/ensure/', UiProjectEnsureView.as_view(), name='ui-project-ensure'),
    path('codegen/pipeline/parse/', codegen_pipeline_parse, name='codegen-pipeline-parse'),
    path(
        'codegen/pipeline/to-case-steps/',
        codegen_pipeline_to_case_steps,
        name='codegen-pipeline-to-case-steps',
    ),
    path('codegen/pipeline/detail/<int:pk>/', codegen_pipeline_detail, name='codegen-pipeline-detail'),
    path(
        'codegen/pipeline/<int:pk>/generate-plan/',
        codegen_pipeline_generate_plan,
        name='codegen-pipeline-generate-plan',
    ),
    path('codegen/pipeline/<int:pk>/plan/', codegen_pipeline_update_plan, name='codegen-pipeline-update-plan'),
    path(
        'codegen/pipeline/<int:pk>/confirm-plan/',
        codegen_pipeline_confirm_plan,
        name='codegen-pipeline-confirm-plan',
    ),
    path(
        'codegen/pipeline/<int:pk>/generate-scripts/',
        codegen_pipeline_generate_scripts,
        name='codegen-pipeline-generate-scripts',
    ),
    path('', include(router.urls)),
]

# 添加媒体文件路由
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
