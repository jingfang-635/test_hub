import os
import json
import time
import uuid
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from PyPDF2 import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfFileReader as PdfReader
    except ImportError:
        # PyPDF2 未安装时降级为 None，避免模块导入失败影响 URL 路由解析
        # （Vercel 等 Serverless 环境只安装核心依赖）
        PdfReader = None

try:
    import docx
except ImportError:
    docx = None
from django.conf import settings
from django.core.files.storage import default_storage

from .models import RequirementDocument, RequirementAnalysis, BusinessRequirement, GeneratedTestCase, AnalysisTask

logger = logging.getLogger(__name__)


def _check_pdf_available():
    """检查 PyPDF2 是否可用，不可用时抛出友好错误"""
    if PdfReader is None:
        raise RuntimeError('PyPDF2 未安装，PDF 文档解析功能不可用。请安装 requirements_optional.txt')


class DocumentProcessor:
    """文档处理服务（优先通过本地 Tika Server 解析）"""

    TIKA_SUPPORTED_TYPES = ('pdf', 'docx', 'doc', 'pptx', 'xlsx', 'html', 'htm')

    @classmethod
    def extract_text_via_tika(cls, file_path: str) -> str:
        """通过 Apache Tika Server 提取文本"""
        import requests
        from .models import KnowledgeBaseLLMConfig

        tika_url = KnowledgeBaseLLMConfig.get_tika_server_url()
        endpoint = f'{tika_url}/tika'

        with open(file_path, 'rb') as file:
            data = file.read()

        response = requests.put(
            endpoint,
            data=data,
            headers={'Accept': 'text/plain; charset=utf-8'},
            timeout=120,
        )
        response.raise_for_status()
        # Tika 可能返回 latin-1，优先按 utf-8 解码
        if response.encoding is None or response.encoding.lower() in ('iso-8859-1', 'latin-1'):
            text = response.content.decode('utf-8', errors='ignore')
        else:
            text = response.text
        return (text or '').strip()

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """从PDF文件提取文本（本地回退）"""
        _check_pdf_available()
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"PDF文本提取失败: {e}")
            return f"PDF文本提取失败: {str(e)}"
    
    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """从Word文档提取文本（本地回退）"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Word文档文本提取失败: {e}")
            return f"Word文档文本提取失败: {str(e)}"
    
    @staticmethod
    def extract_text_from_txt(file_path: str) -> str:
        """从文本文件提取文本"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk') as file:
                    return file.read().strip()
            except Exception as e:
                logger.error(f"文本文件读取失败: {e}")
                return f"文本文件读取失败: {str(e)}"
        except Exception as e:
            logger.error(f"文本文件读取失败: {e}")
            return f"文本文件读取失败: {str(e)}"

    @classmethod
    def _extract_text_local(cls, file_path: str, document_type: str) -> str:
        """本地解析回退"""
        if document_type == 'pdf':
            return cls.extract_text_from_pdf(file_path)
        if document_type == 'docx':
            return cls.extract_text_from_docx(file_path)
        if document_type in ('txt', 'md'):
            return cls.extract_text_from_txt(file_path)
        return "不支持的文档类型"
    
    @classmethod
    def extract_text_by_type(cls, file_path: str, document_type: str) -> str:
        """根据文件路径与文档类型提取文本（优先 Tika Server）"""
        doc_type = (document_type or '').lower()

        # 纯文本直接本地读取，无需走 Tika
        if doc_type in ('txt', 'md'):
            return cls.extract_text_from_txt(file_path)

        if doc_type in cls.TIKA_SUPPORTED_TYPES or doc_type in ('pdf', 'docx'):
            try:
                text = cls.extract_text_via_tika(file_path)
                if text:
                    logger.info(f"Tika 解析成功: type={doc_type}, chars={len(text)}")
                    return text
                logger.warning(f"Tika 返回空文本，尝试本地回退: type={doc_type}")
            except Exception as e:
                logger.warning(f"Tika 解析失败，尝试本地回退: type={doc_type}, error={e}")

            return cls._extract_text_local(file_path, doc_type)

        return "不支持的文档类型"

    @classmethod
    def extract_text(cls, document) -> str:
        """根据文档类型提取文本（兼容需求文档 / 知识库文档）"""
        return cls.extract_text_by_type(document.file.path, document.document_type)


class KnowledgeVectorizer:
    """知识库文档分块与向量化"""

    EMBEDDING_BATCH_SIZE = 16

    @staticmethod
    def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
        content = (text or '').strip()
        if not content:
            return []

        chunk_size = max(int(chunk_size or 500), 50)
        chunk_overlap = max(0, min(int(chunk_overlap or 0), chunk_size - 1))

        chunks = []
        start = 0
        length = len(content)
        while start < length:
            end = min(start + chunk_size, length)
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= length:
                break
            start = max(0, end - chunk_overlap)
            if start >= end:
                start = end
        return chunks

    @classmethod
    def embed_texts(cls, texts: List[str], llm_config) -> List[List[float]]:
        if not texts:
            return []
        if not llm_config or not (llm_config.embedding_api_key or '').strip():
            raise RuntimeError('未配置知识库 Embedding 模型，请先在配置中心完成向量化模型配置')

        import requests

        base_url = (llm_config.embedding_base_url or '').rstrip('/')
        url = f'{base_url}/embeddings'
        headers = {
            'Authorization': f'Bearer {llm_config.embedding_api_key.strip()}',
            'Content-Type': 'application/json',
        }

        vectors: List[List[float]] = []
        for i in range(0, len(texts), cls.EMBEDDING_BATCH_SIZE):
            batch = texts[i:i + cls.EMBEDDING_BATCH_SIZE]
            payload = {
                'model': llm_config.embedding_model_name or 'text-embedding-v3',
                'input': batch,
            }
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            if response.status_code >= 400:
                detail = response.text[:500]
                raise RuntimeError(f'Embedding API 调用失败({response.status_code}): {detail}')

            data = response.json()
            items = data.get('data') or []
            items = sorted(items, key=lambda x: x.get('index', 0))
            if len(items) != len(batch):
                raise RuntimeError('Embedding API 返回数量与请求分块不一致')
            for item in items:
                embedding = item.get('embedding')
                if not isinstance(embedding, list) or not embedding:
                    raise RuntimeError('Embedding API 返回空向量')
                vectors.append(embedding)
        return vectors

    @classmethod
    def vectorize_document(cls, document) -> int:
        """对已提取文本的文档进行分块向量化，返回分块数"""
        from .models import KnowledgeBaseLLMConfig, KnowledgeDocumentChunk

        knowledge_base = document.knowledge_base
        if not knowledge_base.enable_vectorization:
            document.chunks.all().delete()
            document.chunk_count = 0
            document.is_vectorized = False
            document.save(update_fields=['chunk_count', 'is_vectorized', 'updated_at'])
            return 0

        text = (document.extracted_text or '').strip()
        if not text:
            raise RuntimeError('文档文本为空，无法进行向量化')

        chunks = cls.split_text(
            text,
            chunk_size=knowledge_base.chunk_size,
            chunk_overlap=knowledge_base.chunk_overlap,
        )
        if not chunks:
            raise RuntimeError('文本分块结果为空，无法进行向量化')

        llm_config = KnowledgeBaseLLMConfig.get_active_config()
        embeddings = cls.embed_texts(chunks, llm_config)

        document.chunks.all().delete()
        KnowledgeDocumentChunk.objects.bulk_create([
            KnowledgeDocumentChunk(
                document=document,
                knowledge_base=knowledge_base,
                chunk_index=index,
                content=content,
                embedding=embeddings[index],
                char_count=len(content),
            )
            for index, content in enumerate(chunks)
        ])

        document.chunk_count = len(chunks)
        document.is_vectorized = True
        document.save(update_fields=['chunk_count', 'is_vectorized', 'updated_at'])
        return len(chunks)


class AIService:
    """AI服务类 - 模拟大模型调用"""
    
    @staticmethod
    async def analyze_requirements(text: str, document_title: str = "") -> Dict[str, Any]:
        """
        先进的需求分析 - 使用新的智能分析引擎
        
        Args:
            text: 需求文档文本内容
            document_title: 文档标题
            
        Returns:
            Dict包含分析报告、结构化需求等信息
        """
        try:
            # 直接导入并使用先进分析器
            from apps.requirement_analysis.advanced_analyzer import advanced_analyzer
            
            logger.info(f"使用先进分析器分析需求，文档标题: {document_title}")
            
            # 使用先进分析器进行分析
            result = await advanced_analyzer.analyze_requirements_advanced(text, document_title)
            
            # 转换为原系统期望的格式
            analysis_report = result.get("analysis_report", "")
            structured_requirements = result.get("structured_requirements", {})
            requirements_list = structured_requirements.get("requirements", [])
            
            # 计算分析时间（模拟）
            import time
            analysis_time = time.time() % 10 + 2  # 2-12秒之间的模拟时间
            
            logger.info(f"先进需求分析完成，识别需求{len(requirements_list)}个")
            
            return {
                "analysis_report": analysis_report,
                "requirements": requirements_list,
                "requirements_count": len(requirements_list),
                "analysis_time": analysis_time,
                "quality_assessment": result.get("quality_assessment", {}),
                "risk_analysis": result.get("risk_analysis", {})
            }
            
        except Exception as e:
            logger.error(f"先进需求分析失败: {e}")
            logger.info("使用备用分析方法")
            # fallback到原来的分析逻辑
            return await AIService._fallback_analyze_requirements(text, document_title)
    
    @staticmethod
    async def _fallback_analyze_requirements(text: str, document_title: str = "") -> Dict[str, Any]:
        """备用需求分析方法"""
        # 模拟AI分析过程
        await asyncio.sleep(2)
        
        # 这里应该调用真实的大模型API
        # 现在返回改进的模拟数据
        analysis_report = f"""
# 需求分析报告

## 文档概述
基于提供的需求文档"{document_title}"，共识别出以下主要需求模块和功能点。

## 主要功能模块
1. 用户管理模块
2. 数据处理模块  
3. 报告生成模块
4. 系统配置模块

## 详细需求分析
基于文档内容分析，识别出以下具体需求：

### 功能需求
- 用户认证和权限管理
- 数据录入和维护功能
- 业务流程处理
- 报表和统计功能

### 非功能需求
- 系统性能要求：响应时间 < 3秒
- 安全性要求：数据加密存储
- 可用性要求：99.5%系统可用率
- 兼容性要求：支持主流浏览器

## 风险评估
- 技术实现风险：中等
- 进度风险：低
- 资源风险：低

## 建议
建议采用敏捷开发模式，分阶段实施各功能模块。

分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        # 生成基础的结构化需求
        requirements = [
            {
                "requirement_id": "REQ-001",
                "requirement_name": "用户认证管理", 
                "requirement_type": "functional",
                "parent_requirement": None,
                "module": "用户管理",
                "requirement_level": "high",
                "reviewer": "admin",
                "estimated_hours": 16,
                "description": "作为一名系统用户，我希望通过用户名和密码登录系统，这样可以确保系统安全性并获得个性化服务。",
                "acceptance_criteria": "用户能够使用有效凭证成功登录系统，无效凭证登录失败，系统记录登录日志。"
            },
            {
                "requirement_id": "REQ-002",
                "requirement_name": "数据管理功能",
                "requirement_type": "functional", 
                "parent_requirement": None,
                "module": "数据管理",
                "requirement_level": "high",
                "reviewer": "admin",
                "estimated_hours": 24,
                "description": "作为一名数据操作员，我希望能够对系统数据进行增删改查操作，这样可以有效管理业务信息。",
                "acceptance_criteria": "数据操作功能正常，数据完整性得到保证，操作权限控制有效。"
            },
            {
                "requirement_id": "REQ-003",
                "requirement_name": "报表统计功能",
                "requirement_type": "functional",
                "parent_requirement": None,
                "module": "报表管理",
                "requirement_level": "medium", 
                "reviewer": "admin",
                "estimated_hours": 20,
                "description": "作为一名管理人员，我希望能够生成各类业务报表和统计图表，这样可以直观了解业务数据和趋势。",
                "acceptance_criteria": "系统能够生成多种格式的报表，数据准确，支持导出功能。"
            }
        ]
        
        return {
            "analysis_report": analysis_report,
            "requirements": requirements,
            "requirements_count": len(requirements)
        }
    
    @staticmethod
    async def generate_test_cases(requirement: BusinessRequirement, test_level: str, test_priority: str, count: int) -> List[Dict[str, Any]]:
        """生成测试用例 - 大模型A"""
        # 模拟AI生成过程
        await asyncio.sleep(1)
        
        # 生成唯一case_id的辅助函数
        def generate_unique_case_id(req, base_index):
            """生成唯一的测试用例ID"""
            base_case_id = f"TC-{req.requirement_id}-{base_index:03d}"
            case_id = base_case_id
            counter = 1
            
            # 检查是否已存在，如果存在则添加后缀
            from .models import GeneratedTestCase
            while GeneratedTestCase.objects.filter(requirement=req, case_id=case_id).exists():
                case_id = f"{base_case_id}_{counter}"
                counter += 1
            
            return case_id
        
        # 获取该需求现有测试用例的数量，作为起始索引
        from .models import GeneratedTestCase
        existing_count = GeneratedTestCase.objects.filter(requirement=requirement).count()
        
        # 根据需求生成测试用例
        test_cases = []
        for i in range(count):
            case_id = generate_unique_case_id(requirement, existing_count + i + 1)
            
            # 根据需求类型生成不同的测试用例
            if "登录" in requirement.requirement_name:
                test_cases.append({
                    "case_id": case_id,
                    "title": f"验证用户使用有效凭证登录系统的认证流程和权限获取",
                    "priority": test_priority,
                    "precondition": "系统正常运行，测试用户账号已创建",
                    "test_steps": "1. 打开登录页面\n2. 输入有效的用户名和密码\n3. 点击登录按钮\n4. 检查登录结果和页面跳转",
                    "expected_result": "用户成功登录系统，跳转到主页面，显示用户信息和相应权限功能"
                })
            elif "数据" in requirement.requirement_name:
                test_cases.append({
                    "case_id": case_id,
                    "title": f"测试数据录入功能在各种输入场景下的验证机制和保存结果",
                    "priority": test_priority,
                    "precondition": "系统正常运行，用户已登录具备数据操作权限",
                    "test_steps": "1. 进入数据录入页面\n2. 填写必填字段信息\n3. 提交数据\n4. 验证数据保存结果",
                    "expected_result": "数据成功保存到数据库，页面显示保存成功提示，可以查询到新录入的数据"
                })
            elif "报告" in requirement.requirement_name:
                test_cases.append({
                    "case_id": case_id,
                    "title": f"验证报告生成功能在不同格式和数据量下的处理能力和输出质量",
                    "priority": test_priority, 
                    "precondition": "系统正常运行，存在可用于生成报告的数据",
                    "test_steps": "1. 进入报告生成页面\n2. 选择报告类型和参数\n3. 点击生成报告\n4. 检查生成的报告内容和格式",
                    "expected_result": "报告成功生成，内容准确完整，格式符合要求，可以正常下载"
                })
            else:
                test_cases.append({
                    "case_id": case_id,
                    "title": f"验证{requirement.requirement_name}功能的基本操作流程和预期结果",
                    "priority": test_priority,
                    "precondition": "系统正常运行，用户已登录",
                    "test_steps": f"1. 访问{requirement.requirement_name}功能\n2. 执行主要操作步骤\n3. 验证操作结果",
                    "expected_result": f"{requirement.requirement_name}功能正常工作，操作结果符合预期"
                })
        
        return test_cases
    
    @staticmethod
    async def review_test_cases(test_cases: List[GeneratedTestCase], review_criteria: str) -> Dict[str, Any]:
        """评审测试用例 - 大模型B"""
        # 模拟AI评审过程
        await asyncio.sleep(1.5)
        
        reviewed_cases = []
        for test_case in test_cases:
            # 模拟评审逻辑
            review_score = 85  # 模拟评分
            
            review_comments = f"""
评审意见:
1. 测试用例标题清晰明确，能够准确描述测试目的
2. 测试步骤详细具体，具有良好的可执行性
3. 预期结果明确，便于验证
4. 建议补充异常场景的测试覆盖

评审分数: {review_score}/100
评审状态: 通过
"""
            
            reviewed_cases.append({
                "test_case_id": test_case.id,
                "review_score": review_score,
                "review_comments": review_comments.strip(),
                "status": "reviewed" if review_score >= 80 else "rejected"
            })
        
        return {
            "reviewed_cases": reviewed_cases,
            "overall_score": sum(case["review_score"] for case in reviewed_cases) / len(reviewed_cases),
            "pass_rate": len([case for case in reviewed_cases if case["status"] == "reviewed"]) / len(reviewed_cases) * 100
        }


class RequirementAnalysisService:
    """需求分析服务"""
    
    @classmethod
    def create_analysis_task(cls, document: RequirementDocument, task_type: str) -> AnalysisTask:
        """创建分析任务"""
        task_id = f"{task_type}_{uuid.uuid4().hex[:8]}"
        
        task = AnalysisTask.objects.create(
            task_id=task_id,
            task_type=task_type,
            document=document,
            status='pending'
        )
        
        return task
    
    @classmethod
    async def process_document_analysis(cls, document: RequirementDocument) -> RequirementAnalysis:
        """处理文档分析"""
        # 创建分析任务
        task = cls.create_analysis_task(document, 'requirement_analysis')
        
        try:
            # 更新任务状态
            task.status = 'running'
            task.started_at = datetime.now()
            task.progress = 10
            task.save()
            
            # 提取文档文本
            if not document.extracted_text:
                document.extracted_text = DocumentProcessor.extract_text(document)
                document.save()
            
            task.progress = 30
            task.save()
            
            # 调用AI分析
            start_time = time.time()
            analysis_result = await AIService.analyze_requirements(
                document.extracted_text, 
                document.title
            )
            analysis_time = time.time() - start_time
            
            task.progress = 70
            task.save()
            
            # 创建分析记录
            analysis = RequirementAnalysis.objects.create(
                document=document,
                analysis_report=analysis_result['analysis_report'],
                requirements_count=analysis_result['requirements_count'],
                analysis_time=analysis_time
            )
            
            # 保存需求数据
            for req_data in analysis_result['requirements']:
                BusinessRequirement.objects.create(
                    analysis=analysis,
                    **req_data
                )
            
            # 更新文档状态
            document.status = 'analyzed'
            document.save()
            
            # 完成任务
            task.status = 'completed'
            task.completed_at = datetime.now()
            task.progress = 100
            task.result = analysis_result
            task.save()
            
            return analysis
            
        except Exception as e:
            logger.error(f"文档分析失败: {e}")
            
            # 更新任务状态
            task.status = 'failed'
            task.error_message = str(e)
            task.completed_at = datetime.now()
            task.save()
            
            # 更新文档状态
            document.status = 'failed'
            document.save()
            
            raise e
    
    @classmethod
    async def generate_test_cases_for_requirements(cls, requirement_ids: List[int], test_level: str, test_priority: str, test_case_count: int) -> List[GeneratedTestCase]:
        """为需求生成测试用例"""
        generated_cases = []
        
        for req_id in requirement_ids:
            try:
                requirement = BusinessRequirement.objects.get(id=req_id)
                
                # 调用AI生成测试用例
                test_cases_data = await AIService.generate_test_cases(
                    requirement, test_level, test_priority, test_case_count
                )
                
                # 保存生成的测试用例
                for case_data in test_cases_data:
                    test_case = GeneratedTestCase.objects.create(
                        requirement=requirement,
                        case_id=case_data['case_id'],
                        title=case_data['title'],
                        priority=case_data['priority'],
                        precondition=case_data['precondition'],
                        test_steps=case_data['test_steps'],
                        expected_result=case_data['expected_result'],
                        generated_by_ai='AI-A'
                    )
                    generated_cases.append(test_case)
                    
            except BusinessRequirement.DoesNotExist:
                logger.error(f"需求ID {req_id} 不存在")
                continue
            except Exception as e:
                logger.error(f"为需求 {req_id} 生成测试用例失败: {e}")
                continue
        
        return generated_cases
    
    @classmethod
    async def review_test_cases(cls, test_case_ids: List[int], review_criteria: str) -> Dict[str, Any]:
        """评审测试用例"""
        test_cases = GeneratedTestCase.objects.filter(id__in=test_case_ids)
        
        # 调用AI评审
        review_result = await AIService.review_test_cases(list(test_cases), review_criteria)
        
        # 更新测试用例状态
        for case_review in review_result['reviewed_cases']:
            try:
                test_case = GeneratedTestCase.objects.get(id=case_review['test_case_id'])
                test_case.status = case_review['status']
                test_case.review_comments = case_review['review_comments']
                test_case.reviewed_by_ai = 'AI-B'
                test_case.save()
            except GeneratedTestCase.DoesNotExist:
                logger.error(f"测试用例ID {case_review['test_case_id']} 不存在")
                continue
        
        return review_result