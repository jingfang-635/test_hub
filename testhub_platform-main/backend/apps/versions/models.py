from django.db import models
from django.utils import timezone
from apps.users.models import User
from apps.projects.models import Project

VERSION_STATUS_CHOICES = [
    ('draft', '草稿'),
    ('in_progress', '进行中'),
    ('released', '已发布'),
    ('deprecated', '已废弃'),
]

class Version(models.Model):
    """版本模型"""
    projects = models.ManyToManyField(Project, related_name='versions', verbose_name='关联项目')
    name = models.CharField(max_length=100, verbose_name='版本名称')
    description = models.TextField(blank=True, verbose_name='版本描述')
    is_baseline = models.BooleanField(default=False, verbose_name='是否为基线版本')
    status = models.CharField(max_length=20, choices=VERSION_STATUS_CHOICES, default='draft', verbose_name='状态')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    owner = models.CharField(max_length=200, blank=True, default='', verbose_name='负责人')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'versions'
        verbose_name = '版本'
        verbose_name_plural = '版本'
        ordering = ['-created_at']
