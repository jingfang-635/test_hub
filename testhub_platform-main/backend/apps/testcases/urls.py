from django.urls import path
from . import views

urlpatterns = [
    # 测试用例相关
    path('', views.TestCaseListCreateView.as_view(), name='testcase-list'),
    path('<int:pk>/', views.TestCaseDetailView.as_view(), name='testcase-detail'),
    # 用例详情-UI自动化 tab：只读结构化步骤（动作/页面/元素/选择器/输入值）
    path('<int:pk>/ui_step_details/', views.TestCaseUiStepDetailView.as_view(), name='testcase-ui-step-details'),
    # 批量导入
    path('import/', views.import_testcases_view, name='testcase-import'),
]