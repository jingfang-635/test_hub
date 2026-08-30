<template>
  <div class="requirement-analysis">
    <!-- 配置引导弹出窗口 -->
    <div v-if="showConfigGuide && !checkingConfig" class="modal-overlay" @click.self="showConfigGuide = false" :key="modalKey">
      <div class="guide-config-modal">
      <div class="guide-header">
        <svg class="guide-icon" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
          <path d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372z" fill="#f59e0b"/>
          <path d="M464 336a48 48 0 1 0 96 0 48 48 0 1 0-96 0zm72 112h-48c-4.4 0-8 3.6-8 8v272c0 4.4 3.6 8 8 8h48c4.4 0 8-3.6 8-8V456c0-4.4-3.6-8-8-8z" fill="#f59e0b"/>
        </svg>
        <div class="guide-title">
          <h2>{{ $t('configGuide.title') }}</h2>
          <p>{{ $t('configGuide.subtitle') }}</p>
        </div>
      </div>

      <div class="config-groups">
        <div class="config-group">
          <div class="group-label">{{ $t('configGuide.modelConfig') }}</div>
          <div class="config-items-row">
            <div class="config-item-inline" :class="getConfigItemClass('writer_model')">
              <span class="status-symbol" v-html="getStatusSymbol('writer_model')"></span>
              <span class="config-label">{{ $t('configGuide.caseWriter') }}</span>
              <span class="config-name" v-if="configStatus.writer_model.name">{{ configStatus.writer_model.name }}</span>
              <span class="status-text" v-if="!configStatus.writer_model.configured">{{ $t('configGuide.unconfigured') }}</span>
              <span class="status-text warning" v-else-if="!configStatus.writer_model.enabled">{{ $t('configGuide.disabled') }}</span>
            </div>

            <div class="config-item-inline" :class="getConfigItemClass('reviewer_model')">
              <span class="status-symbol" v-html="getStatusSymbol('reviewer_model')"></span>
              <span class="config-label">{{ $t('configGuide.caseReviewer') }}</span>
              <span class="config-name" v-if="configStatus.reviewer_model.name">{{ configStatus.reviewer_model.name }}</span>
              <span class="status-text" v-if="!configStatus.reviewer_model.configured">{{ $t('configGuide.unconfigured') }}</span>
              <span class="status-text warning" v-else-if="!configStatus.reviewer_model.enabled">{{ $t('configGuide.disabled') }}</span>
            </div>
          </div>
        </div>

        <div class="config-group">
          <div class="group-label">{{ $t('configGuide.promptConfig') }}</div>
          <div class="config-items-row">
            <div class="config-item-inline" :class="getConfigItemClass('writer_prompt')">
              <span class="status-symbol" v-html="getStatusSymbol('writer_prompt')"></span>
              <span class="config-label">{{ $t('configGuide.caseWriter') }}</span>
              <span class="config-name" v-if="configStatus.writer_prompt.name">{{ configStatus.writer_prompt.name }}</span>
              <span class="status-text" v-if="!configStatus.writer_prompt.configured">{{ $t('configGuide.unconfigured') }}</span>
              <span class="status-text warning" v-else-if="!configStatus.writer_prompt.enabled">{{ $t('configGuide.disabled') }}</span>
            </div>

            <div class="config-item-inline" :class="getConfigItemClass('reviewer_prompt')">
              <span class="status-symbol" v-html="getStatusSymbol('reviewer_prompt')"></span>
              <span class="config-label">{{ $t('configGuide.caseReviewer') }}</span>
              <span class="config-name" v-if="configStatus.reviewer_prompt.name">{{ configStatus.reviewer_prompt.name }}</span>
              <span class="status-text" v-if="!configStatus.reviewer_prompt.configured">{{ $t('configGuide.unconfigured') }}</span>
              <span class="status-text warning" v-else-if="!configStatus.reviewer_prompt.enabled">{{ $t('configGuide.disabled') }}</span>
            </div>
          </div>
        </div>

        <div class="config-group">
          <div class="group-label">{{ $t('configGuide.generationConfig') }}</div>
          <div class="config-items-row">
            <div class="config-item-inline" :class="getConfigItemClass('generation_config')">
              <span class="status-symbol" v-html="getStatusSymbol('generation_config')"></span>
              <span class="config-label">{{ $t('configGuide.generationSettings') }}</span>
              <span class="config-name" v-if="configStatus.generation_config && configStatus.generation_config.name">{{ configStatus.generation_config.name }}</span>
              <span class="status-text" v-if="!configStatus.generation_config || !configStatus.generation_config.configured">{{ $t('configGuide.unconfigured') }}</span>
            </div>
          </div>
        </div>
      </div>

        <div class="guide-actions">
          <button class="generate-manual-btn" @click="goToConfig">
            {{ $t('configGuide.goToConfig') }}
          </button>
          <div class="skip-action" @click="showConfigGuide = false">
            {{ $t('configGuide.configureLater') }}
          </div>
        </div>
      </div>
    </div>

    <div class="page-body" v-if="!isGenerating && !showResults">
      <!-- 输出模式设置 -->
      <section class="section-card">
        <h3 class="section-title">
          <span class="section-title-icon output-icon" aria-hidden="true"></span>
          {{ $t('requirementAnalysis.outputModeTitle') }}
        </h3>
        <p class="section-desc">{{ $t('requirementAnalysis.outputModeDesc') }}</p>
        <div class="output-mode-selector">
          <label class="mode-option" :class="{ active: globalOutputMode === 'stream' }">
            <input type="radio" v-model="globalOutputMode" value="stream">
            <div class="mode-content">
              <div class="mode-icon stream">⚡</div>
              <div class="mode-text">
                <div class="mode-title">{{ $t('requirementAnalysis.realtimeStream') }}</div>
                <div class="mode-desc">{{ $t('requirementAnalysis.realtimeStreamDesc') }}</div>
              </div>
            </div>
          </label>
          <label class="mode-option" :class="{ active: globalOutputMode === 'complete' }">
            <input type="radio" v-model="globalOutputMode" value="complete">
            <div class="mode-content">
              <div class="mode-icon complete">📄</div>
              <div class="mode-text">
                <div class="mode-title">{{ $t('requirementAnalysis.completeOutput') }}</div>
                <div class="mode-desc">{{ $t('requirementAnalysis.completeOutputDesc') }}</div>
              </div>
            </div>
          </label>
        </div>
      </section>

      <!-- 需求来源选择 -->
      <div class="source-type-grid">
        <button
          type="button"
          class="source-card"
          :class="{ active: activeSource === 'manual' }"
          @click="activeSource = 'manual'">
          <div class="source-card-title">{{ $t('requirementAnalysis.sourceManual') }}</div>
          <div class="source-card-icon manual">✏️</div>
          <p class="source-card-desc">{{ $t('requirementAnalysis.sourceManualDesc') }}</p>
        </button>
        <button
          type="button"
          class="source-card"
          :class="{ active: activeSource === 'upload' }"
          @click="activeSource = 'upload'">
          <div class="source-card-title">{{ $t('requirementAnalysis.sourceUpload') }}</div>
          <div class="source-card-icon upload">📑</div>
          <p class="source-card-desc">{{ $t('requirementAnalysis.sourceUploadDesc') }}</p>
        </button>
        <button
          type="button"
          class="source-card"
          :class="{ active: activeSource === 'knowledge' }"
          @click="activeSource = 'knowledge'">
          <div class="source-card-title">{{ $t('requirementAnalysis.sourceKnowledge') }}</div>
          <div class="source-card-icon knowledge">📚</div>
          <p class="source-card-desc">{{ $t('requirementAnalysis.sourceKnowledgeDesc') }}</p>
        </button>
        <button
          type="button"
          class="source-card"
          :class="{ active: activeSource === 'figma' }"
          @click="activeSource = 'figma'">
          <div class="source-card-title">{{ $t('requirementAnalysis.sourceFigma') }}</div>
          <div class="source-card-icon figma">🎨</div>
          <p class="source-card-desc">{{ $t('requirementAnalysis.sourceFigmaDesc') }}</p>
        </button>
        <button
          type="button"
          class="source-card"
          :class="{ active: activeSource === 'feishu' }"
          @click="activeSource = 'feishu'">
          <div class="source-card-title">{{ $t('requirementAnalysis.sourceFeishu') }}</div>
          <div class="source-card-icon feishu">📄</div>
          <p class="source-card-desc">{{ $t('requirementAnalysis.sourceFeishuDesc') }}</p>
        </button>
      </div>

      <!-- 手动输入 -->
      <section class="section-card" v-if="activeSource === 'manual'">
        <h3 class="section-title">
          <span class="panel-emoji">✏️</span>
          {{ $t('requirementAnalysis.manualInputTitle') }}
        </h3>
        <div class="input-form">
          <div class="form-group">
            <label>{{ $t('requirementAnalysis.requirementTitle') }} <span class="required">*</span></label>
            <input
              v-model="manualInput.title"
              type="text"
              class="form-input"
              :placeholder="$t('requirementAnalysis.titlePlaceholder')">
          </div>

          <div class="form-group">
            <label>{{ $t('requirementAnalysis.requirementDescription') }} <span class="required">*</span></label>
            <textarea
              v-model="manualInput.description"
              class="form-textarea"
              rows="8"
              :placeholder="$t('requirementAnalysis.descriptionPlaceholder')"></textarea>
            <div class="char-count">{{ manualInput.description.length }}/2000</div>
          </div>

          <div class="form-group">
            <label>{{ $t('requirementAnalysis.associatedProject') }}</label>
            <select v-model="manualInput.selectedProject" class="form-select">
              <option value="">{{ $t('requirementAnalysis.selectProject') }}</option>
              <option v-for="project in projects" :key="project.id" :value="project.id">
                {{ project.name }}
              </option>
            </select>
          </div>

          <button
            class="generate-manual-btn"
            @click="generateFromManualInput"
            :disabled="!canGenerateManual || isGenerating">
            <span v-if="isGenerating">{{ $t('requirementAnalysis.generating') }}</span>
            <span v-else>{{ $t('requirementAnalysis.generateButton') }}</span>
          </button>
        </div>
      </section>

      <!-- 文档上传 -->
      <section class="section-card" v-if="activeSource === 'upload'">
        <h3 class="section-title">
          <span class="panel-emoji">📑</span>
          {{ $t('requirementAnalysis.uploadTitle') }}
        </h3>
        <div class="upload-area"
             @dragover.prevent
             @drop="handleDrop"
             :class="{ 'drag-over': isDragOver }"
             @dragenter="isDragOver = true"
             @dragleave="isDragOver = false">
          <div v-if="!selectedFile" class="upload-placeholder">
            <i class="upload-icon">📁</i>
            <p>{{ $t('requirementAnalysis.dragDropText') }}</p>
            <p class="upload-hint">{{ $t('requirementAnalysis.supportedFormats') }}</p>
            <input
              type="file"
              ref="fileInput"
              @change="handleFileSelect"
              accept=".pdf,.doc,.docx,.txt,.md"
              style="display: none;">
            <button class="select-file-btn" @click="$refs.fileInput.click()">
              {{ $t('requirementAnalysis.selectFile') }}
            </button>
          </div>

          <div v-else class="file-selected">
            <div class="file-info">
              <i class="file-icon">📄</i>
              <div class="file-details">
                <p class="file-name">{{ selectedFile.name }}</p>
                <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
              </div>
              <button class="remove-file" @click="removeFile">❌</button>
            </div>
          </div>
        </div>

        <div v-if="selectedFile" class="document-info">
          <div class="form-group">
            <label>{{ $t('requirementAnalysis.documentTitle') }}</label>
            <input
              v-model="documentTitle"
              type="text"
              class="form-input"
              :placeholder="$t('requirementAnalysis.documentPlaceholder')">
          </div>

          <div class="form-group">
            <label>{{ $t('requirementAnalysis.associatedProject') }}</label>
            <select v-model="selectedProject" class="form-select">
              <option value="">{{ $t('requirementAnalysis.selectProject') }}</option>
              <option v-for="project in projects" :key="project.id" :value="project.id">
                {{ project.name }}
              </option>
            </select>
          </div>

          <button
            class="generate-btn"
            @click="generateFromDocument"
            :disabled="!documentTitle || isGenerating">
            <span v-if="isGenerating">{{ $t('requirementAnalysis.generating') }}</span>
            <span v-else>{{ $t('requirementAnalysis.generateButton') }}</span>
          </button>
        </div>
      </section>

      <!-- 知识库需求 -->
      <section class="section-card" v-if="activeSource === 'knowledge'">
        <h3 class="section-title">
          <span class="panel-emoji">📚</span>
          {{ $t('requirementAnalysis.sourceKnowledge') }}
        </h3>

        <div class="kb-form-grid">
          <div class="form-group">
            <label>{{ $t('requirementAnalysis.selectKnowledgeBase') }}</label>
            <select v-model="knowledgeForm.knowledgeBaseId" class="form-select">
              <option value="">{{ $t('requirementAnalysis.selectKnowledgeBasePlaceholder') }}</option>
              <option v-for="base in knowledgeBases" :key="base.id" :value="base.id">
                {{ base.name }}{{ base.document_count != null ? ` (${base.document_count})` : '' }}
              </option>
            </select>
            <p v-if="!knowledgeBasesLoading && knowledgeBases.length === 0" class="kb-empty-hint">
              {{ $t('requirementAnalysis.noKnowledgeBaseHint') }}
              <router-link to="/ai-generation/knowledge-base">{{ $t('requirementAnalysis.goToKnowledgeBase') }}</router-link>
            </p>
          </div>
          <div class="form-group">
            <label>{{ $t('requirementAnalysis.associatedProject') }}</label>
            <select v-model="knowledgeForm.selectedProject" class="form-select">
              <option value="">{{ $t('requirementAnalysis.selectProject') }}</option>
              <option v-for="project in projects" :key="project.id" :value="project.id">
                {{ project.name }}
              </option>
            </select>
          </div>
        </div>

        <div class="kb-search-settings">
          <div class="form-group kb-search-type">
            <label>{{ $t('requirementAnalysis.searchType') }}</label>
            <div class="search-type-group">
              <button
                type="button"
                class="search-type-btn"
                :class="{ active: knowledgeForm.searchType === 'hybrid' }"
                @click="knowledgeForm.searchType = 'hybrid'">
                {{ $t('requirementAnalysis.searchHybrid') }}
              </button>
              <button
                type="button"
                class="search-type-btn"
                :class="{ active: knowledgeForm.searchType === 'semantic' }"
                @click="knowledgeForm.searchType = 'semantic'">
                {{ $t('requirementAnalysis.searchSemantic') }}
              </button>
              <button
                type="button"
                class="search-type-btn"
                :class="{ active: knowledgeForm.searchType === 'keyword' }"
                @click="knowledgeForm.searchType = 'keyword'">
                {{ $t('requirementAnalysis.searchKeyword') }}
              </button>
            </div>
          </div>

          <div class="form-group kb-slider-group">
            <label>{{ $t('requirementAnalysis.similarityThreshold') }}</label>
            <div class="slider-row">
              <input
                type="range"
                min="0"
                max="100"
                v-model.number="knowledgeForm.similarity"
                class="form-slider">
              <span class="slider-value">{{ knowledgeForm.similarity }}%</span>
            </div>
          </div>

          <div class="form-group kb-recall-group">
            <label>{{ $t('requirementAnalysis.recallCount') }}</label>
            <input
              type="number"
              min="1"
              max="50"
              v-model.number="knowledgeForm.recallCount"
              class="form-input form-input-sm">
          </div>

          <div class="form-group kb-slider-group" v-if="knowledgeForm.searchType === 'hybrid'">
            <label>{{ $t('requirementAnalysis.vectorRatio') }}</label>
            <div class="slider-row">
              <input
                type="range"
                min="0"
                max="100"
                v-model.number="knowledgeForm.vectorRatio"
                class="form-slider">
              <span class="slider-value">{{ knowledgeForm.vectorRatio }}%</span>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>{{ $t('requirementAnalysis.searchContent') }}</label>
          <div class="kb-search-row">
            <input
              v-model="knowledgeForm.query"
              type="text"
              class="form-input"
              :placeholder="$t('requirementAnalysis.searchContentPlaceholder')">
            <button
              type="button"
              class="kb-search-btn"
              :disabled="!knowledgeForm.knowledgeBaseId || !knowledgeForm.query.trim()"
              @click="searchKnowledgeBase">
              {{ $t('requirementAnalysis.search') }}
            </button>
          </div>
        </div>
      </section>

      <!-- Figma 解析 -->
      <section class="section-card figma-panel" v-if="activeSource === 'figma'">
        <h3 class="section-title">{{ $t('requirementAnalysis.sourceFigma') }}</h3>
        <p class="section-desc">{{ $t('requirementAnalysis.figmaHint') }}</p>

        <div class="form-group">
          <label>{{ $t('requirementAnalysis.figmaOnlineLink') }} <span class="required">*</span></label>
          <div class="parse-link-row">
            <input
              v-model="figmaForm.url"
              type="text"
              class="form-input"
              :placeholder="$t('requirementAnalysis.figmaLinkPlaceholder')">
            <button
              type="button"
              class="parse-btn"
              :disabled="!figmaForm.url.trim() || figmaForm.parsing || isGenerating"
              @click="parseFigmaLink">
              <span v-if="figmaForm.parsing">{{ $t('requirementAnalysis.figmaParsing') }}</span>
              <span v-else>{{ $t('requirementAnalysis.confirmParse') }}</span>
            </button>
          </div>
        </div>

        <div class="figma-options-row">
          <label class="figma-radio">
            <input type="radio" v-model="figmaForm.contentMode" value="full">
            <span>{{ $t('requirementAnalysis.figmaFullContent') }}</span>
          </label>
          <label class="figma-radio">
            <input type="radio" v-model="figmaForm.contentMode" value="incremental">
            <span>{{ $t('requirementAnalysis.figmaIncrementalContent') }}</span>
          </label>
          <label class="figma-checkbox">
            <input type="checkbox" v-model="figmaForm.useAiStructure">
            <span>{{ $t('requirementAnalysis.figmaUseAiStructure') }}</span>
          </label>
        </div>

        <div class="form-group figma-project-group">
          <label>{{ $t('requirementAnalysis.associatedProject') }}</label>
          <select v-model="figmaForm.selectedProject" class="form-select">
            <option value="">{{ $t('requirementAnalysis.selectProject') }}</option>
            <option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.name }}
            </option>
          </select>
        </div>

        <div v-if="figmaForm.parsed" class="figma-preview">
          <div class="form-group">
            <label>{{ $t('requirementAnalysis.requirementTitle') }} <span class="required">*</span></label>
            <input
              v-model="figmaForm.title"
              type="text"
              class="form-input"
              :placeholder="$t('requirementAnalysis.titlePlaceholder')">
          </div>

          <div class="form-group">
            <label>{{ $t('requirementAnalysis.figmaContentPreview') }}</label>
            <textarea
              v-model="figmaForm.content"
              class="form-textarea feishu-content-preview"
              rows="10"></textarea>
            <div class="char-count">{{ figmaForm.content.length }} {{ $t('requirementAnalysis.feishuChars') }}</div>
          </div>

          <button
            class="generate-manual-btn"
            @click="generateFromFigma"
            :disabled="!canGenerateFigma || isGenerating">
            <span v-if="isGenerating">{{ $t('requirementAnalysis.generating') }}</span>
            <span v-else>{{ $t('requirementAnalysis.generateButton') }}</span>
          </button>
        </div>
      </section>

      <!-- 飞书文档 -->
      <section class="section-card feishu-panel" v-if="activeSource === 'feishu'">
        <h3 class="section-title">
          <span class="panel-emoji">📄</span>
          {{ $t('requirementAnalysis.sourceFeishu') }}
        </h3>
        <p class="section-desc">{{ $t('requirementAnalysis.feishuHint') }}</p>

        <div class="feishu-oauth-bar">
          <template v-if="feishuOAuth.connected">
            <span class="feishu-oauth-status">
              {{ $t('requirementAnalysis.feishuConnectedAs', { name: feishuOAuth.feishuName || 'Feishu' }) }}
            </span>
            <button type="button" class="feishu-oauth-secondary" @click="disconnectFeishu" :disabled="feishuOAuth.loading">
              {{ $t('requirementAnalysis.feishuDisconnect') }}
            </button>
          </template>
          <template v-else>
            <button
              type="button"
              class="feishu-oauth-primary"
              :disabled="feishuOAuth.loading"
              @click="connectFeishu">
              <span v-if="feishuOAuth.loading">{{ $t('requirementAnalysis.feishuConnecting') }}</span>
              <span v-else>{{ $t('requirementAnalysis.feishuConnect') }}</span>
            </button>
          </template>
        </div>

        <div class="form-group">
          <label>{{ $t('requirementAnalysis.feishuDocLink') }} <span class="required">*</span></label>
          <div class="parse-link-row">
            <input
              v-model="feishuForm.url"
              type="text"
              class="form-input"
              :placeholder="$t('requirementAnalysis.feishuLinkPlaceholder')">
            <button
              type="button"
              class="parse-btn"
              :disabled="!feishuForm.url.trim() || feishuForm.parsing || !feishuOAuth.connected"
              @click="parseFeishuLink">
              <span v-if="feishuForm.parsing">{{ $t('requirementAnalysis.feishuParsing') }}</span>
              <span v-else>{{ $t('requirementAnalysis.confirmParse') }}</span>
            </button>
          </div>
        </div>

        <div v-if="feishuForm.parsed" class="feishu-preview">
          <div class="form-group">
            <label>{{ $t('requirementAnalysis.requirementTitle') }} <span class="required">*</span></label>
            <input
              v-model="feishuForm.title"
              type="text"
              class="form-input"
              :placeholder="$t('requirementAnalysis.titlePlaceholder')">
          </div>

          <div class="form-group">
            <label>{{ $t('requirementAnalysis.feishuContentPreview') }}</label>
            <textarea
              v-model="feishuForm.content"
              class="form-textarea feishu-content-preview"
              rows="10"></textarea>
            <div class="char-count">{{ feishuForm.content.length }} {{ $t('requirementAnalysis.feishuChars') }}</div>
          </div>

          <div class="form-group">
            <label>{{ $t('requirementAnalysis.associatedProject') }}</label>
            <select v-model="feishuForm.selectedProject" class="form-select">
              <option value="">{{ $t('requirementAnalysis.selectProject') }}</option>
              <option v-for="project in projects" :key="project.id" :value="project.id">
                {{ project.name }}
              </option>
            </select>
          </div>

          <button
            class="generate-manual-btn"
            @click="generateFromFeishu"
            :disabled="!canGenerateFeishu || isGenerating">
            <span v-if="isGenerating">{{ $t('requirementAnalysis.generating') }}</span>
            <span v-else>{{ $t('requirementAnalysis.generateButton') }}</span>
          </button>
        </div>
      </section>
    </div>

    <!-- 生成进度和结果 -->
    <div v-if="isGenerating || showResults" class="generation-progress">
      <div class="progress-card">
        <h3>
          {{ $t('requirementAnalysis.aiGeneratingTitle') }}
          <span class="current-mode-badge">
            ({{ globalOutputMode === 'stream' ? $t('requirementAnalysis.realtimeStream') : $t('requirementAnalysis.completeOutput') }})
          </span>
        </h3>
        <div class="progress-info">
          <div class="progress-item">
            <span class="label">{{ $t('requirementAnalysis.taskId') }}</span>
            <span class="value">{{ currentTaskId || $t('requirementAnalysis.preparing') }}</span>
          </div>
          <div class="progress-item">
            <span class="label">{{ $t('requirementAnalysis.currentStatus') }}</span>
            <span class="value">{{ showResults ? $t('requirementAnalysis.generationComplete') : progressText }}</span>
          </div>
        </div>

        <div v-if="streamedContent" class="stream-content-display">
          <div class="stream-header">
            <span class="stream-title">{{ $t('requirementAnalysis.realtimeGeneratedContent') }}</span>
            <span class="stream-status">{{ $t('requirementAnalysis.characters', { count: streamedContent.length }) }}</span>
          </div>
          <div class="stream-content" v-html="formatMarkdown(streamedContent)"></div>
        </div>

        <div v-if="streamedReviewContent" class="stream-content-display" style="margin-top: 15px;">
          <div class="stream-header">
            <span class="stream-title">{{ $t('requirementAnalysis.aiReviewComments') }}</span>
            <span class="stream-status">{{ $t('requirementAnalysis.characters', { count: streamedReviewContent.length }) }}</span>
          </div>
          <div class="stream-content" v-html="formatMarkdown(streamedReviewContent)"></div>
        </div>

        <div v-if="finalTestCases" class="stream-content-display" style="margin-top: 15px;">
          <div class="stream-header">
            <span class="stream-title">
              {{ $t('requirementAnalysis.finalVersionTestCases') }}
              <span v-if="isGenerating" class="streaming-indicator">{{ $t('requirementAnalysis.generating') }}</span>
            </span>
            <span class="stream-status">{{ $t('requirementAnalysis.characters', { count: finalTestCases.length }) }}</span>
          </div>
          <div class="stream-content final-testcases" v-html="formatMarkdown(finalTestCases)"></div>
        </div>

        <div class="progress-steps">
          <div class="step" :class="{ active: currentStep >= 1 }">
            <span class="step-number">1</span>
            <span class="step-text">{{ $t('requirementAnalysis.stepAnalysis') }}</span>
          </div>
          <div class="step" :class="{ active: currentStep >= 2 }">
            <span class="step-number">2</span>
            <span class="step-text">{{ $t('requirementAnalysis.stepWriting') }}</span>
          </div>
          <div v-if="showReviewStep" class="step" :class="{ active: currentStep >= 3 }">
            <span class="step-number">3</span>
            <span class="step-text">{{ $t('requirementAnalysis.stepReview') }}</span>
          </div>
          <div class="step" :class="{ active: currentStep >= (showReviewStep ? 4 : 3) }">
            <span class="step-number">{{ showReviewStep ? 4 : 3 }}</span>
            <span class="step-text">{{ $t('requirementAnalysis.stepComplete') }}</span>
          </div>
        </div>

        <div v-if="showResults" class="completion-actions">
          <button class="download-btn" @click="downloadTestCases">
            <span>📥 {{ $t('requirementAnalysis.downloadExcel') }}</span>
          </button>
          <button class="save-btn" @click="saveToTestCaseRecords">
            <span>💾 {{ $t('requirementAnalysis.saveToRecords') }}</span>
          </button>
          <button class="new-generation-btn" @click="resetGeneration">
            <span>📝 {{ $t('requirementAnalysis.newGeneration') }}</span>
          </button>
        </div>
        <button v-else class="cancel-generation-btn" @click="cancelGeneration">
          {{ $t('requirementAnalysis.cancelGeneration') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/utils/api'
import { getKnowledgeBases } from '@/api/requirement-analysis'
import { ElMessage } from 'element-plus'
import * as XLSX from 'xlsx'
import { useUserStore } from '@/stores/user'

export default {
  name: 'RequirementAnalysisView',
  data() {
    return {
      // 全局输出模式设置
      globalOutputMode: 'stream',  // 默认使用流式输出

      // 需求来源：manual | upload | knowledge | figma | feishu
      activeSource: 'manual',

      // 手动输入需求
      manualInput: {
        title: '',
        description: '',
        selectedProject: ''
      },

      // 知识库检索表单（与 /configuration/knowledge-base 同源）
      knowledgeBases: [],
      knowledgeBasesLoading: false,
      knowledgeForm: {
        knowledgeBaseId: '',
        selectedProject: '',
        searchType: 'hybrid',
        similarity: 50,
        recallCount: 5,
        vectorRatio: 70,
        query: ''
      },

      // Figma 解析表单
      figmaForm: {
        url: '',
        title: '',
        content: '',
        sourceUrl: '',
        contentMode: 'full',
        useAiStructure: true,
        selectedProject: '',
        parsing: false,
        parsed: false
      },

      // 飞书文档表单
      feishuForm: {
        url: '',
        title: '',
        content: '',
        sourceUrl: '',
        selectedProject: '',
        parsing: false,
        parsed: false
      },
      feishuOAuth: {
        connected: false,
        feishuName: '',
        loading: false
      },

      // 文件上传
      selectedFile: null,
      documentTitle: '',
      selectedProject: '',
      projects: [],
      isDragOver: false,

      // 生成状态
      isGenerating: false,
      currentTaskId: null,
      progressText: '',
      currentStep: 0,
      pollInterval: null,
      eventSource: null,  // SSE连接
      streamedContent: '',  // 流式接收的内容
      streamedReviewContent: '',  // 流式接收的评审内容
      finalTestCases: '',  // 最终版用例
      hasShownCompletionMessage: false,  // 是否已经显示过完成消息
      showReviewStep: true,  // 是否显示评审步骤（根据生成配置决定）

      // 生成结果
      showResults: false,
      generationResult: null,

      // AI配置状态
      configStatus: {
        overall_status: 'unknown',
        message: '',
        writer_model: {
          configured: false,
          enabled: false,
          name: null,
          provider: null,
          id: null,
          required: true
        },
        writer_prompt: {
          configured: false,
          enabled: false,
          name: null,
          id: null,
          required: true
        },
        reviewer_model: {
          configured: false,
          enabled: false,
          name: null,
          id: null,
          required: true
        },
        reviewer_prompt: {
          configured: false,
          enabled: false,
          name: null,
          id: null,
          required: true
        },
        generation_config: {
          configured: false,
          enabled: false,
          name: null,
          id: null,
          required: true,
          default_output_mode: null
        }
      },
      showConfigGuide: false,
      checkingConfig: true,
      modalKey: 0  // 用于强制重新渲染弹窗
    }
  },

  computed: {
    canGenerateManual() {
      return this.manualInput.title.trim() &&
             this.manualInput.description.trim() &&
             this.manualInput.description.length <= 2000
    },
    canGenerateFeishu() {
      return this.feishuForm.parsed &&
             this.feishuForm.title.trim() &&
             this.feishuForm.content.trim()
    },
    canGenerateFigma() {
      return this.figmaForm.parsed &&
             this.figmaForm.title.trim() &&
             this.figmaForm.content.trim()
    }
  },

  async mounted() {
    this.progressText = this.$t('requirementAnalysis.preparing')
    this.loadProjects()
    this.loadKnowledgeBases()
    this.checkConfigStatus()
    const handled = await this.handleFeishuOAuthCallback()
    if (!handled) {
      await this.loadFeishuOAuthStatus()
    }
  },

  watch: {
    activeSource(val) {
      if (val === 'feishu') {
        this.loadFeishuOAuthStatus()
      } else if (val === 'knowledge') {
        this.loadKnowledgeBases()
      }
    }
  },

  activated() {
    // 当从其他页面返回时，重新检查配置状态
    // 立即隐藏弹窗和遮罩层，强制重新渲染
    this.showConfigGuide = false
    this.checkingConfig = true
    this.modalKey += 1  // 改变key值，强制重新渲染弹窗

    // 延迟检查配置，确保页面完全加载后再显示弹窗
    setTimeout(async () => {
      await this.checkConfigStatus()
      this.loadKnowledgeBases()
      const handled = await this.handleFeishuOAuthCallback()
      if (!handled) {
        await this.loadFeishuOAuthStatus()
      }
    }, 200)
  },

  beforeUnmount() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval)
    }
    // 停止token自动刷新定时器
    const userStore = useUserStore()
    userStore.stopAutoRefresh()
  },

  methods: {
    searchKnowledgeBase() {
      if (!this.knowledgeForm.knowledgeBaseId) {
        ElMessage.warning(this.$t('requirementAnalysis.selectKnowledgeBasePlaceholder'))
        return
      }
      if (!this.knowledgeForm.query.trim()) return
      ElMessage.info(this.$t('requirementAnalysis.featureComingSoon'))
    },

    async loadKnowledgeBases() {
      // 与「系统配置 / 知识库」同一数据源：GET /requirement-analysis/knowledge-bases/
      this.knowledgeBasesLoading = true
      try {
        const response = await getKnowledgeBases({ is_active: true })
        let list = []
        if (response.data?.results && Array.isArray(response.data.results)) {
          list = response.data.results
        } else if (Array.isArray(response.data)) {
          list = response.data
        }
        this.knowledgeBases = list
        if (
          this.knowledgeForm.knowledgeBaseId &&
          !list.some((b) => String(b.id) === String(this.knowledgeForm.knowledgeBaseId))
        ) {
          this.knowledgeForm.knowledgeBaseId = ''
        }
      } catch (error) {
        this.knowledgeBases = []
        console.error(this.$t('requirementAnalysis.loadKnowledgeBasesFailed'), error)
        if (error.response?.status !== 401) {
          ElMessage.error(this.$t('requirementAnalysis.loadKnowledgeBasesFailed'))
        }
      } finally {
        this.knowledgeBasesLoading = false
      }
    },

    async parseFigmaLink() {
      if (!this.figmaForm.url.trim() || this.figmaForm.parsing || this.isGenerating) return
      this.figmaForm.parsing = true
      this.figmaForm.parsed = false
      try {
        const response = await api.post('/requirement-analysis/figma/fetch/', {
          url: this.figmaForm.url.trim()
        })
        const data = response.data || {}
        this.figmaForm.title = data.title || ''
        this.figmaForm.content = data.content || ''
        this.figmaForm.sourceUrl = data.source_url || this.figmaForm.url.trim()
        this.figmaForm.parsed = true
        ElMessage.success(this.$t('requirementAnalysis.figmaParseSuccess'))
        // 解析成功后按当前生成配置自动生成用例
        await this.generateFromFigma()
      } catch (error) {
        const payload = error.response?.data || {}
        const code = payload.code || ''
        const msg = payload.error || error.message
        const i18nKey = {
          not_configured: 'figmaErrorNotConfigured',
          invalid_url: 'figmaErrorInvalidUrl',
          unsupported_url: 'figmaErrorUnsupportedUrl',
          permission_denied: 'figmaErrorPermission',
          not_found: 'figmaErrorNotFound',
          empty_content: 'figmaErrorEmpty',
          auth_failed: 'figmaErrorAuth',
          content_too_long: 'figmaErrorTooLong',
          network_error: 'figmaErrorNetwork',
          figma_server_error: 'figmaErrorNetwork'
        }[code]
        ElMessage.error(i18nKey ? this.$t(`requirementAnalysis.${i18nKey}`) : msg)
      } finally {
        this.figmaForm.parsing = false
      }
    },

    async generateFromFigma() {
      if (!this.canGenerateFigma) {
        ElMessage.error(this.$t('requirementAnalysis.fillRequiredInfo'))
        return
      }
      await this.startGeneration(
        this.figmaForm.title.trim(),
        this.figmaForm.content,
        this.figmaForm.selectedProject,
        this.globalOutputMode,
        {
          sourceType: 'figma',
          sourceUrl: this.figmaForm.sourceUrl || this.figmaForm.url.trim()
        }
      )
    },

    async loadFeishuOAuthStatus() {
      try {
        const response = await api.get('/requirement-analysis/feishu/oauth_status/')
        const data = response.data || {}
        this.feishuOAuth.connected = !!data.connected
        this.feishuOAuth.feishuName = data.feishu_name || ''
      } catch (e) {
        this.feishuOAuth.connected = false
        this.feishuOAuth.feishuName = ''
      }
    },

    clearFeishuOAuthQuery(extraKeys = []) {
      const q = { ...(this.$route?.query || {}) }
      ;['feishu_oauth', 'feishu_msg', 'code', 'state', 'error', ...extraKeys].forEach((k) => {
        delete q[k]
      })
      this.$router.replace({ path: this.$route.path, query: q }).catch(() => {})
    },

    /**
     * 处理飞书 OAuth 回跳。
     * @returns {Promise<boolean>} 是否已处理 code 换票（调用方无需再 load status）
     */
    async handleFeishuOAuthCallback() {
      const q = this.$route?.query || {}

      // 前端中转：飞书直接回调到本页并带上 code/state
      if (q.code && q.state) {
        this.activeSource = 'feishu'
        this.feishuOAuth.loading = true
        try {
          const response = await api.post('/requirement-analysis/feishu/oauth_complete/', {
            code: q.code,
            state: q.state
          })
          const data = response.data || {}
          this.feishuOAuth.connected = !!data.connected
          this.feishuOAuth.feishuName = data.feishu_name || ''
          if (this.feishuOAuth.connected) {
            ElMessage.success(this.$t('requirementAnalysis.feishuOAuthSuccess'))
          } else {
            ElMessage.error(this.$t('requirementAnalysis.feishuOAuthError'))
          }
        } catch (error) {
          const payload = error.response?.data || {}
          ElMessage.error(payload.error || this.$t('requirementAnalysis.feishuOAuthError'))
          this.feishuOAuth.connected = false
          this.feishuOAuth.feishuName = ''
        } finally {
          this.feishuOAuth.loading = false
          this.clearFeishuOAuthQuery()
        }
        return true
      }

      const status = q.feishu_oauth
      if (!status) return false

      this.activeSource = 'feishu'
      if (status === 'success') {
        ElMessage.success(this.$t('requirementAnalysis.feishuOAuthSuccess'))
        await this.loadFeishuOAuthStatus()
      } else if (status === 'denied') {
        ElMessage.warning(this.$t('requirementAnalysis.feishuOAuthDenied'))
      } else {
        ElMessage.error(q.feishu_msg || this.$t('requirementAnalysis.feishuOAuthError'))
      }
      this.clearFeishuOAuthQuery()
      return status === 'success'
    },

    async connectFeishu() {
      this.feishuOAuth.loading = true
      try {
        const response = await api.get('/requirement-analysis/feishu/oauth_authorize_url/')
        const url = response.data?.authorize_url
        if (!url) {
          ElMessage.error(this.$t('requirementAnalysis.feishuOAuthError'))
          return
        }
        window.location.href = url
      } catch (error) {
        const payload = error.response?.data || {}
        const code = payload.code || ''
        if (code === 'not_configured') {
          ElMessage.error(this.$t('requirementAnalysis.feishuErrorNotConfigured'))
        } else {
          ElMessage.error(payload.error || this.$t('requirementAnalysis.feishuOAuthError'))
        }
        this.feishuOAuth.loading = false
      }
    },

    async disconnectFeishu() {
      this.feishuOAuth.loading = true
      try {
        await api.post('/requirement-analysis/feishu/oauth_disconnect/')
        this.feishuOAuth.connected = false
        this.feishuOAuth.feishuName = ''
        this.feishuForm.parsed = false
        ElMessage.success(this.$t('requirementAnalysis.feishuDisconnectSuccess'))
      } catch (error) {
        ElMessage.error(error.response?.data?.error || error.message)
      } finally {
        this.feishuOAuth.loading = false
      }
    },

    async parseFeishuLink() {
      if (!this.feishuForm.url.trim()) return
      if (!this.feishuOAuth.connected) {
        ElMessage.warning(this.$t('requirementAnalysis.feishuNeedConnect'))
        return
      }
      this.feishuForm.parsing = true
      this.feishuForm.parsed = false
      try {
        const response = await api.post('/requirement-analysis/feishu/fetch/', {
          url: this.feishuForm.url.trim()
        })
        const data = response.data || {}
        this.feishuForm.title = data.title || ''
        this.feishuForm.content = data.content || ''
        this.feishuForm.sourceUrl = data.source_url || this.feishuForm.url.trim()
        this.feishuForm.parsed = true
        ElMessage.success(this.$t('requirementAnalysis.feishuParseSuccess'))
      } catch (error) {
        const payload = error.response?.data || {}
        const code = payload.code || ''
        const msg = payload.error || error.message
        const i18nKey = {
          not_configured: 'feishuErrorNotConfigured',
          invalid_url: 'feishuErrorInvalidUrl',
          unsupported_url: 'feishuErrorUnsupportedUrl',
          permission_denied: 'feishuErrorPermission',
          unsupported_wiki_type: 'feishuErrorWikiType',
          empty_content: 'feishuErrorEmpty',
          auth_failed: 'feishuErrorAuth',
          content_too_long: 'feishuErrorTooLong',
          network_error: 'feishuErrorNetwork',
          feishu_server_error: 'feishuErrorNetwork',
          need_oauth: 'feishuErrorNeedOAuth',
          need_reauth: 'feishuErrorNeedReauth'
        }[code]
        if (code === 'need_oauth' || code === 'need_reauth') {
          this.feishuOAuth.connected = false
        }
        ElMessage.error(i18nKey ? this.$t(`requirementAnalysis.${i18nKey}`) : msg)
      } finally {
        this.feishuForm.parsing = false
      }
    },

    async generateFromFeishu() {
      if (!this.canGenerateFeishu) {
        ElMessage.error(this.$t('requirementAnalysis.fillRequiredInfo'))
        return
      }
      await this.startGeneration(
        this.feishuForm.title.trim(),
        this.feishuForm.content,
        this.feishuForm.selectedProject,
        this.globalOutputMode,
        {
          sourceType: 'feishu',
          sourceUrl: this.feishuForm.sourceUrl || this.feishuForm.url.trim()
        }
      )
    },

    async loadProjects() {
      // 与「项目与版本」一致：仅加载关联了 AI用例生成(ai_generation) 的项目
      try {
        const pageSize = 100
        let page = 1
        let hasMore = true
        const all = []
        while (hasMore) {
          const response = await api.get('/projects/', {
            params: {
              project_type: 'ai_generation',
              page,
              page_size: pageSize
            }
          })
          const results = response.data.results || response.data || []
          const list = Array.isArray(results) ? results : []
          all.push(...list)
          if (!response.data.results || list.length < pageSize) {
            hasMore = false
          } else {
            page++
          }
        }
        this.projects = all
      } catch (error) {
        console.error(this.$t('requirementAnalysis.loadProjectsFailed'), error)
      }
    },

    async checkConfigStatus() {
      try {
        this.checkingConfig = true
        const response = await api.get('/requirement-analysis/config/check/')
        this.configStatus = response.data

        // 判断逻辑：只有当"用例编写模型"、"用例评审模型"、"用例编写提示词"和"用例评审提示词"都配置且启用时，才不显示弹框
        const writerModelReady = response.data.writer_model &&
                                response.data.writer_model.configured &&
                                response.data.writer_model.enabled

        const reviewerModelReady = response.data.reviewer_model &&
                                  response.data.reviewer_model.configured &&
                                  response.data.reviewer_model.enabled

        const writerPromptReady = response.data.writer_prompt &&
                                 response.data.writer_prompt.configured &&
                                 response.data.writer_prompt.enabled

        const reviewerPromptReady = response.data.reviewer_prompt &&
                                   response.data.reviewer_prompt.configured &&
                                   response.data.reviewer_prompt.enabled

        // 检查生成行为配置
        const generationConfigReady = response.data.generation_config &&
                                      response.data.generation_config.configured

        // 只有五项都准备好时才不显示引导弹框
        if (writerModelReady && reviewerModelReady && writerPromptReady && reviewerPromptReady && generationConfigReady) {
          this.showConfigGuide = false

          // 如果生成配置允许用户修改，则使用配置的默认输出模式
          if (response.data.generation_config && response.data.generation_config.default_output_mode) {
            this.globalOutputMode = response.data.generation_config.default_output_mode
          }

          // 根据生成配置的enable_auto_review决定是否显示评审步骤
          if (response.data.generation_config && response.data.generation_config.enable_auto_review !== null) {
            this.showReviewStep = response.data.generation_config.enable_auto_review
          } else {
            this.showReviewStep = true  // 默认显示
          }
        } else {
          this.showConfigGuide = true
        }
      } catch (error) {
        console.error('Failed to check config status:', error)
        // 如果检查失败，默认不显示引导，避免影响正常使用
        this.showConfigGuide = false
        this.checkingConfig = false
      } finally {
        this.checkingConfig = false
      }
    },

    goToConfig() {
      // 智能判断跳转目标：优先跳转到未配置/未启用的页面
      // 优先级：必需配置 > 可选配置，提示词 > 模型

      // 0. 首先检查生成行为配置（generation_config）
      if (!this.configStatus.generation_config || !this.configStatus.generation_config.configured) {
        this.$router.push('/configuration/generation-config')
        return
      }

      // 1. 优先检查必需的提示词配置（writer_prompt）
      if (!this.configStatus.writer_prompt.configured || !this.configStatus.writer_prompt.enabled) {
        this.$router.push('/configuration/prompt-config')
        return
      }

      // 2. 检查必需的模型配置（writer_model）
      if (!this.configStatus.writer_model.configured || !this.configStatus.writer_model.enabled) {
        this.$router.push('/configuration/ai-model')
        return
      }

      // 3. 检查可选的评审提示词（reviewer_prompt）
      if (!this.configStatus.reviewer_prompt.configured || !this.configStatus.reviewer_prompt.enabled) {
        this.$router.push('/configuration/prompt-config')
        return
      }

      // 4. 检查可选的评审模型（reviewer_model）
      if (!this.configStatus.reviewer_model.configured || !this.configStatus.reviewer_model.enabled) {
        this.$router.push('/configuration/ai-model')
        return
      }

      // 默认跳转到生成行为配置
      this.$router.push('/configuration/generation-config')
    },

    goToPromptConfig() {
      this.$router.push('/configuration/prompt-config')
    },

    getConfigItemClass(configKey) {
      const config = this.configStatus[configKey]
      if (config.enabled) {
        return 'status-enabled'
      } else if (config.configured) {
        return 'status-disabled'
      } else {
        return 'status-unconfigured'
      }
    },

    getStatusIcon(configKey) {
      const config = this.configStatus[configKey]
      if (config.enabled) {
        // 绿色对号
        return '<path d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm193.5 301.7l-210.6 292c-12.7 17.7-39 17.7-51.7 0L318.5 484.9c-3.8-5.3 0-12.7 6.5-12.7h46.9c10.2 0 19.9 4.9 25.9 13.3l71.2 98.8 157.2-218c6-8.3 15.6-13.3 25.9-13.3H699c6.5 0 10.3 7.4 6.5 12.7z" fill="#27ae60"/>'
      } else if (config.configured) {
        // 禁用图标（灰色圆圈和斜线）
        return '<path d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372zm128-412c0 4.4-3.6 8-8 8H392c-4.4 0-8-3.6-8-8v-48c0-4.4 3.6-8 8-8h240c4.4 0 8 3.6 8 8v48z" fill="#95a5a6"/>'
      } else {
        // 红色叉号
        return '<path d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm165.4 618.2l-66-70.7c-10.6-10.1-28.1-10.1-38.8 0l-66.7 71.5-66.7-71.5c-10.6-10.1-28.1-10.1-38.8 0l-66 70.7c-9.9 10.6-9.9 27.4 0 38l66 70.7c10.6 10.1 28.1 10.1 38.8 0l66.7-71.5 66.7 71.5c10.6 10.1 28.1 10.1 38.8 0l66-70.7c9.9-10.6 9.9-27.4 0-38z" fill="#e74c3c"/>'
      }
    },

    getStatusSymbol(configKey) {
      const config = this.configStatus[configKey]
      if (config.enabled) {
        // 绿色对勾
        return '<span style="color: #27ae60; font-size: 18px;">✓</span>'
      } else if (config.configured) {
        // 禁用图标
        return '<span style="color: #95a5a6; font-size: 18px;">○</span>'
      } else {
        // 红色叉号
        return '<span style="color: #e74c3c; font-size: 18px;">✗</span>'
      }
    },

    handleDrop(event) {
      event.preventDefault()
      this.isDragOver = false
      const files = event.dataTransfer.files
      if (files.length > 0) {
        this.handleFileSelect({ target: { files } })
      }
    },

    handleFileSelect(event) {
      const file = event.target.files[0]
      if (file) {
        const allowedTypes = [
          'application/pdf',
          'application/msword',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'text/plain',
          'text/markdown',
          'text/x-markdown'
        ]

        if (allowedTypes.includes(file.type) ||
            file.name.match(/\.(pdf|doc|docx|txt|md)$/i)) {
          this.selectedFile = file
          this.documentTitle = file.name.replace(/\.[^/.]+$/, "")
        } else {
          ElMessage.error(this.$t('requirementAnalysis.invalidFileFormatDetail'))
        }
      }
    },

    removeFile() {
      this.selectedFile = null
      this.documentTitle = ''
      this.$refs.fileInput.value = ''
    },

    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },

    async generateFromManualInput() {
      if (!this.canGenerateManual) {
        ElMessage.error(this.$t('requirementAnalysis.fillRequiredInfo'))
        return
      }

      const requirementText = `${this.$t('requirementAnalysis.requirementTitle')}: ${this.manualInput.title}\n\n${this.$t('requirementAnalysis.requirementDescription')}:\n${this.manualInput.description}`

      await this.startGeneration(
        this.manualInput.title,
        requirementText,
        this.manualInput.selectedProject,
        this.globalOutputMode  // 使用全局输出模式
      )
    },

    async generateFromDocument() {
      if (!this.selectedFile || !this.documentTitle) {
        ElMessage.error(this.$t('requirementAnalysis.selectFileAndTitle'))
        return
      }

      try {
        // 首先上传并提取文档内容
        const formData = new FormData()
        formData.append('title', this.documentTitle)
        formData.append('file', this.selectedFile)
        if (this.selectedProject) {
          formData.append('project', this.selectedProject)
        }

        ElMessage.info(this.$t('requirementAnalysis.extractingContent'))
        const uploadResponse = await api.post('/requirement-analysis/documents/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })

        // 提取文档内容
        const extractResponse = await api.get(`/requirement-analysis/documents/${uploadResponse.data.id}/extract_text/`)
        const extractedText = extractResponse.data.extracted_text

        if (!extractedText || extractedText.trim().length === 0) {
          ElMessage.error(this.$t('requirementAnalysis.extractionFailed'))
          return
        }

        const requirementText = `${this.$t('requirementAnalysis.documentTitle')}: ${this.documentTitle}\n\n${this.$t('requirementAnalysis.documentContent')}:\n${extractedText}`

        await this.startGeneration(
          this.documentTitle,
          requirementText,
          this.selectedProject,
          this.globalOutputMode  // 使用全局输出模式
        )

      } catch (error) {
        console.error(this.$t('requirementAnalysis.documentProcessingFailed'), error)
        ElMessage.error(this.$t('requirementAnalysis.documentProcessingFailed') + ': ' + (error.response?.data?.error || error.message))
      }
    },

    async startGeneration(title, requirementText, projectId, outputMode = 'stream', sourceMeta = {}) {
      // 在开始生成前，主动刷新token确保生成过程中不会过期
      try {
        const userStore = useUserStore()
        if (userStore.isTokenExpiringSoon && userStore.refreshToken) {
          console.log('Refreshing token before generation...')
          await userStore.refreshAccessToken()
          console.log('Token refreshed successfully, safe to start generation')
        } else if (userStore.accessToken) {
          console.log('Token status is good, no refresh needed')
        }
      } catch (error) {
        console.error('Token refresh failed:', error)
        ElMessage.error(this.$t('requirementAnalysis.tokenRefreshFailed'))
        return
      }

      this.isGenerating = true
      this.currentStep = 1
      this.progressText = this.$t('requirementAnalysis.creatingTask')
      this.streamedContent = ''  // 清空流式内容
      this.finalTestCases = ''  // 清空最终版用例
      this.streamedReviewContent = ''  // 清空评审内容
      this.hasShownCompletionMessage = false  // 重置完成消息标志位
      this.showResults = false  // 隐藏上一次的结果

      try {
        // 调用新的生成API
        const requestData = {
          title: title,
          requirement_text: requirementText,
          use_writer_model: true,
          use_reviewer_model: true,
          output_mode: outputMode,  // 添加输出模式参数
          source_type: (['manual', 'upload', 'feishu', 'figma'].includes(sourceMeta.sourceType || this.activeSource)
            ? (sourceMeta.sourceType || this.activeSource)
            : 'manual')
        }

        // 如果选择了项目，添加到请求中
        if (projectId) {
          requestData.project = projectId
        }
        if (sourceMeta.sourceUrl) {
          requestData.source_url = sourceMeta.sourceUrl
        }

        const response = await api.post('/requirement-analysis/testcase-generation/generate/', requestData)

        this.currentTaskId = response.data.task_id
        this.progressText = this.$t('requirementAnalysis.taskCreated')

        ElMessage.success(this.$t('requirementAnalysis.generateSuccess'))

        // 根据输出模式选择不同的进度获取方式
        if (outputMode === 'stream') {
          this.startStreamingProgress()
        } else {
          this.startPolling()
        }

      } catch (error) {
        console.error(this.$t('requirementAnalysis.createTaskFailed'), error)
        ElMessage.error(this.$t('requirementAnalysis.createTaskFailed') + ': ' + (error.response?.data?.error || error.message))
        this.isGenerating = false
      }
    },

    startStreamingProgress() {
      // 使用SSE进行流式进度获取
      // 注意：EventSource不使用axios代理，需要直接指向后端服务器
      // 完整的URL路径: /api/requirement-analysis/testcase-generation/{task_id}/stream_progress/

      // 动态获取后端URL：使用当前页面的协议和主机名
      // 在生产环境中(如Docker部署)，通常通过Nginx反向代理访问，端口应该是80或443(与当前页面一致)
      // 而不是直接访问后端端口8000
      const currentOrigin = window.location.origin
      const apiUrl = `${currentOrigin}/api/requirement-analysis/testcase-generation/${this.currentTaskId}/stream_progress/`

      console.log('SSE连接URL:', apiUrl)

      // 创建EventSource（不支持自定义headers，使用withCredentials发送cookie）
      this.eventSource = new EventSource(apiUrl, { withCredentials: true })

      // 监听连接打开事件
      this.eventSource.onopen = (event) => {
        console.log('✅ SSE连接已打开', event)
      }

      this.eventSource.onmessage = (event) => {
        console.log('📨 收到SSE消息:', event.data)

        try {
          const data = JSON.parse(event.data)
          console.log('📦 解析后的数据:', data)

          if (data.type === 'progress') {
            // Update progress status
            if (data.status === 'generating') {
              this.currentStep = 2
              this.progressText = `${this.$t('requirementAnalysis.statusGenerating')} ${data.progress}%`
            } else if (data.status === 'reviewing') {
              this.currentStep = 3
              this.progressText = `${this.$t('requirementAnalysis.statusReviewing')} ${data.progress}%`
            } else if (data.status === 'revising') {
              this.currentStep = 3
              this.progressText = `${this.$t('requirementAnalysis.statusRevising')} ${data.progress}%`
            }
          } else if (data.type === 'content') {
            // Real-time streaming content (case generation)
            console.log('✍️ Received streaming content:', data.content.length, 'characters')
            this.streamedContent += data.content
            this.currentStep = 2
            this.progressText = this.$t('requirementAnalysis.statusGenerating')
          } else if (data.type === 'review_content') {
            // Real-time review content
            console.log('📝 Received review content:', data.content.length, 'characters', 'Total length:', this.streamedReviewContent.length + data.content.length)
            this.streamedReviewContent += data.content
            this.currentStep = 3
            this.progressText = this.$t('requirementAnalysis.statusReviewing')
          } else if (data.type === 'final_content') {
            // Real-time final test cases content
            console.log('🎯 Received final cases content:', data.content.length, 'characters', 'Total length:', this.finalTestCases.length + data.content.length)
            this.finalTestCases += data.content
            this.currentStep = 3
            this.progressText = '🎯 ' + this.$t('requirementAnalysis.statusRevising')
          } else if (data.type === 'status') {
            // Final status
            console.log('📊 Received status update:', data.status)
            if (data.status === 'completed') {
              this.progressText = this.$t('requirementAnalysis.statusCompleted')
              // Fetch final result
              this.fetchFinalResult()
            } else if (data.status === 'failed') {
              this.progressText = this.$t('requirementAnalysis.statusFailed')
              this.handleGenerationError(data.error_message)
            }
          } else if (data.type === 'done') {
            // 流式结束，立即关闭EventSource，获取最终结果
            console.log('✅ 流式传输完成')
            if (this.eventSource) {
              console.log('🔒 关闭SSE连接')
              this.eventSource.close()
              this.eventSource = null
            }
            this.fetchFinalResult()
          }
        } catch (e) {
          console.error('❌ 解析SSE数据失败:', e, '原始数据:', event.data)
        }
      }

      this.eventSource.onerror = (error) => {
        console.log('⚠️ SSE连接事件:', error)

        // 如果EventSource已经被关闭（在onmessage中关闭的），不做任何处理
        if (!this.eventSource) {
          console.log('ℹ️ EventSource已关闭，忽略错误事件')
          return
        }

        console.log('EventSource状态:', {
          readyState: this.eventSource.readyState,
          url: this.eventSource.url
        })

        // 如果任务已经完成或不在生成中，不要降级
        if (this.showResults || !this.isGenerating) {
          console.log('ℹ️ 任务已完成或不在生成中，不降级到轮询')
          // 清理EventSource
          if (this.eventSource) {
            this.eventSource.close()
            this.eventSource = null
          }
          return
        }

        // readyState=2表示连接已关闭，readyState=0表示连接中断
        // EventSource会自动重连（readyState=0），除非是致命错误（readyState=2）
        // 注意：Vercel/Serverless 环境通常不支持 SSE 长连接，降级到轮询是预期行为，不要弹错吓用户
        if (this.eventSource.readyState === 2) {
          console.info('ℹ️ SSE连接已关闭，切换到轮询模式（此为正常降级，Serverless环境下常见）')
          this.eventSource.close()
          this.eventSource = null
          this.startPolling()
        } else if (this.eventSource.readyState === 0) {
          // EventSource正在重连，等待一段时间后检查
          console.log('🔄 SSE正在重连...')
          setTimeout(() => {
            // 如果5秒后还是断开状态，降级到轮询
            if (this.eventSource && this.eventSource.readyState === 0) {
              console.info('ℹ️ SSE重连未恢复，切换到轮询模式（此为正常降级，Serverless环境下常见）')
              this.eventSource.close()
              this.eventSource = null
              this.startPolling()
            }
          }, 5000)
        }
      }
    },

    async fetchFinalResult() {
      try {
        // 修复URL：去掉多余的/api/前缀（axios baseURL已经包含/api）
        const response = await api.get(`/requirement-analysis/testcase-generation/${this.currentTaskId}/progress/`)
        const task = response.data

        this.generationResult = task
        this.showResults = true
        this.isGenerating = false

        // 设置第4步为完成状态
        this.currentStep = 4

        // 设置最终版用例（如果还没有通过流式接收完整）
        if (task.final_test_cases) {
          console.log('📝 Getting final cases from task object')
          // 无论this.finalTestCases是否已有值，都用最新的final_test_cases覆盖
          // 这样确保完整输出模式下也能正确显示最终版用例
          this.finalTestCases = task.final_test_cases
        }

        // 如果评审内容为空，从task对象中获取
        if (!this.streamedReviewContent && task.review_feedback) {
          console.log('📝 Getting review content from task object')
          this.streamedReviewContent = task.review_feedback
        }

        // 如果生成内容为空，从task对象中获取
        if (!this.streamedContent && task.generated_test_cases) {
          console.log('✍️ Getting generated content from task object')
          this.streamedContent = task.generated_test_cases
        }

        if (this.eventSource) {
          this.eventSource.close()
          this.eventSource = null
        }

        // Only show completion message once
        if (!this.hasShownCompletionMessage) {
          ElMessage.success(this.$t('requirementAnalysis.generateCompleteSuccess'))
          this.hasShownCompletionMessage = true
        }
      } catch (error) {
        console.error('Failed to fetch final result:', error)
        ElMessage.error(this.$t('requirementAnalysis.fetchResultFailed'))
        this.isGenerating = false
      }
    },

    handleGenerationError(errorMessage) {
      this.isGenerating = false
      if (this.eventSource) {
        this.eventSource.close()
        this.eventSource = null
      }
      if (this.pollInterval) {
        clearInterval(this.pollInterval)
        this.pollInterval = null
      }
      const detail = errorMessage || this.$t('requirementAnalysis.unknownError')
      ElMessage.error(this.$t('requirementAnalysis.generateFailed') + ': ' + detail)
    },

    startPolling() {
      this.pollInterval = setInterval(async () => {
        try {
          // 修复URL：去掉多余的/api/前缀（axios baseURL已经包含/api）
          const response = await api.get(`/requirement-analysis/testcase-generation/${this.currentTaskId}/progress/`)
          const task = response.data

          console.log(`${this.$t('requirementAnalysis.taskStatus')}: ${task.status}, ${this.$t('requirementAnalysis.progress')}: ${task.progress}%`)

          // 更新进度显示
          if (task.status === 'generating') {
            this.currentStep = 2
            this.progressText = this.$t('requirementAnalysis.statusGenerating')
          } else if (task.status === 'reviewing') {
            this.currentStep = 3
            this.progressText = this.$t('requirementAnalysis.statusReviewing')
          } else if (task.status === 'completed') {
            this.currentStep = 4
            this.progressText = this.$t('requirementAnalysis.statusCompleted')

            // 任务完成，显示结果
            this.generationResult = task
            this.showResults = true
            this.isGenerating = false

            // 设置显示内容（完整输出模式下需要）
            if (task.generated_test_cases) {
              console.log('✍️ Polling mode - Setting generated content')
              this.streamedContent = task.generated_test_cases
            }
            if (task.review_feedback) {
              console.log('📝 Polling mode - Setting review content')
              this.streamedReviewContent = task.review_feedback
            }
            if (task.final_test_cases) {
              console.log('🎯 Polling mode - Setting final test cases')
              this.finalTestCases = task.final_test_cases
            }

            clearInterval(this.pollInterval)
            this.pollInterval = null

            // 只显示一次完成消息
            if (!this.hasShownCompletionMessage) {
              ElMessage.success(this.$t('requirementAnalysis.generateCompleteSuccess'))
              this.hasShownCompletionMessage = true
            }
            return
          } else if (task.status === 'failed') {
            this.progressText = this.$t('requirementAnalysis.statusFailed')
            this.isGenerating = false

            clearInterval(this.pollInterval)
            this.pollInterval = null

            ElMessage.error(this.$t('requirementAnalysis.generateFailed') + ': ' + (task.error_message || this.$t('requirementAnalysis.unknownError')))
            return
          }

        } catch (error) {
          console.error(this.$t('requirementAnalysis.checkProgressFailed'), error)
          // 继续轮询，不中断
        }
      }, 3000) // 每3秒检查一次
    },

    cancelGeneration() {
      if (this.pollInterval) {
        clearInterval(this.pollInterval)
        this.pollInterval = null
      }
      this.isGenerating = false
      this.currentTaskId = null
      ElMessage.info(this.$t('requirementAnalysis.generationCancelled'))
    },

    // 下载测试用例为xlsx文件
    async downloadTestCases() {
      try {
        // 解析最终测试用例内容
        const finalTestCases = this.generationResult.final_test_cases;
        const taskId = this.generationResult.task_id;

        // 创建工作簿
        const workbook = XLSX.utils.book_new();

        // 过滤掉总结和建议部分，只保留测试用例内容
        const filteredContent = this.filterTestCasesOnly(finalTestCases);

        // 尝试解析表格格式的测试用例（参考AutoGenTestCase的做法）
        const tableFormat = this.parseTableFormat(filteredContent);

        let worksheetData = [];

        if (tableFormat.length > 0) {
          // 如果解析到表格格式，直接使用，但要确保表头正确
          worksheetData = tableFormat;

          // 检查并修正表头
          if (worksheetData.length > 0) {
            const header = worksheetData[0];
            for (let i = 0; i < header.length; i++) {
              if (header[i] && header[i].includes('测试步骤')) {
                header[i] = header[i].replace('测试步骤', '操作步骤');
              }
              if (header[i] && header[i].includes('Test Steps')) {
                header[i] = header[i].replace('Test Steps', '操作步骤');
              }
            }
          }
        } else {
          // 否则尝试解析结构化格式
          worksheetData = this.parseStructuredFormat(filteredContent);
        }

        // 将所有单元格中的<br>标签转换为换行符
        worksheetData = worksheetData.map(row =>
          row.map(cell => this.convertBrToNewline(cell))
        );

        // 创建工作表
        const worksheet = XLSX.utils.aoa_to_sheet(worksheetData);

        // 设置列宽
        const colWidths = [
          { wch: 15 }, // 测试用例编号
          { wch: 30 }, // 测试场景
          { wch: 25 }, // 前置条件
          { wch: 40 }, // 操作步骤
          { wch: 30 }, // 预期结果
          { wch: 10 }  // 优先级
        ];
        worksheet['!cols'] = colWidths;

        // 设置表头样式（加粗）
        if (worksheetData.length > 1) {
          for (let col = 0; col < Math.min(6, worksheetData[0].length); col++) {
            const cellAddress = XLSX.utils.encode_cell({ r: 0, c: col });
            if (!worksheet[cellAddress]) continue;
            worksheet[cellAddress].s = {
              font: { bold: true },
              alignment: { horizontal: 'center', vertical: 'center', wrapText: true }
            };
          }

          // 设置自动换行
          for (let row = 1; row < worksheetData.length; row++) {
            for (let col = 0; col < Math.min(6, worksheetData[row].length); col++) {
              const cellAddress = XLSX.utils.encode_cell({ r: row, c: col });
              if (worksheet[cellAddress]) {
                worksheet[cellAddress].s = {
                  alignment: { vertical: 'top', wrapText: true }
                };
              }
            }
          }
        }

        // 将工作表添加到工作簿
        XLSX.utils.book_append_sheet(workbook, worksheet, this.$t('requirementAnalysis.testCaseSheetName'));

        // 生成文件名（包含任务ID和日期）
        const fileName = this.$t('requirementAnalysis.excelFileName', { taskId: taskId, date: new Date().toISOString().slice(0, 10) });

        // 导出文件
        XLSX.writeFile(workbook, fileName);

        ElMessage.success(this.$t('requirementAnalysis.downloadSuccess'));
      } catch (error) {
        console.error(this.$t('requirementAnalysis.downloadFailed'), error);
        ElMessage.error(this.$t('requirementAnalysis.downloadFailed') + ': ' + (error.message || this.$t('requirementAnalysis.unknownError')));
      }
    },

    // 保存到用例记录
    async saveToTestCaseRecords() {
      try {
        // 调用后端API保存到记录
        const response = await api.post(`/requirement-analysis/testcase-generation/${this.generationResult.task_id}/save_to_records/`)

        if (response.data.already_saved) {
          ElMessage.info(this.$t('requirementAnalysis.alreadySaved'))
        } else {
          ElMessage.success(this.$t('requirementAnalysis.saveToRecordsSuccess'))
        }

        // 不跳转，留在当前页面
        // this.$router.push('/generated-testcases')
      } catch (error) {
        console.error(this.$t('requirementAnalysis.saveFailed'), error)
        ElMessage.error(this.$t('requirementAnalysis.saveFailed') + ': ' + (error.response?.data?.error || error.message))
      }
    },

    resetGeneration() {
      // 重置生成状态
      this.isGenerating = false;
      this.currentTaskId = null;
      this.progressText = this.$t('requirementAnalysis.preparing');
      this.currentStep = 0;
      this.showResults = false;
      this.generationResult = null;

      // 清空流式内容和最终版用例
      this.streamedContent = '';
      this.streamedReviewContent = '';
      this.finalTestCases = '';

      if (this.pollInterval) {
        clearInterval(this.pollInterval);
        this.pollInterval = null;
      }

      // 刷新页面以获取最新的配置
      window.location.reload();
    },

    // 格式化日期时间
    formatDateTime(dateTimeString) {
      if (!dateTimeString) return '';
      const date = new Date(dateTimeString);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      return `${year}-${month}-${day} ${hours}:${minutes}`;
    },

    // 格式化Markdown为HTML（简化版）
    formatMarkdown(content) {
      if (!content) return '';

      // 先去除"新增"标记，在markdown转换之前处理
      // 这样可以避免markdown转换后无法匹配的问题
      let html = content
          .replace(/\*\*新增\*\*-/g, '')  // **新增**-xxx -> xxx (保留xxx的原有格式)
          .replace(/新增-/g, '');  // 新增-xxx -> xxx (保留xxx的原有格式)

      // 转义HTML特殊字符
      html = html
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;');

      // 转换Markdown语法
      // 标题 #
      html = html.replace(/^#{6}\s+(.+)$/gm, '<h6>$1</h6>');
      html = html.replace(/^#{5}\s+(.+)$/gm, '<h5>$1</h5>');
      html = html.replace(/^#{4}\s+(.+)$/gm, '<h4>$1</h4>');
      html = html.replace(/^#{3}\s+(.+)$/gm, '<h3>$1</h3>');
      html = html.replace(/^#{2}\s+(.+)$/gm, '<h2>$1</h2>');
      html = html.replace(/^#{1}\s+(.+)$/gm, '<h1>$1</h1>');

      // 粗体 **text** 或 __text__
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');

      // 斜体 *text* 或 _text_
      html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
      html = html.replace(/_(.+?)_/g, '<em>$1</em>');

      // 代码块 ```code```
      html = html.replace(/```([\s\S]+?)```/g, '<pre><code>$1</code></pre>');

      // 行内代码 `code`
      html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

      // 换行符转换为<br>
      html = html.replace(/\n/g, '<br>');

      return html;
    },

    // 将HTML的<br>标签转换为换行符（用于Excel导出）
    convertBrToNewline(text) {
      if (!text) return '';
      return text.replace(/<br\s*\/?>/gi, '\n');
    },

    // 过滤掉总结和建议部分，只保留测试用例内容
    filterTestCasesOnly(content) {
      if (!content) return '';

      const lines = content.split('\n');
      const filteredLines = [];
      let inTestCaseSection = true;

      for (let line of lines) {
        const trimmedLine = line.trim();

        // 检查是否到了总结或建议部分
        if (trimmedLine.includes('总结') ||
            trimmedLine.includes('建议') ||
            trimmedLine.includes('Summary') ||
            trimmedLine.includes('Recommendation') ||
            trimmedLine.includes('最后') ||
            trimmedLine.includes('补充说明')) {
          inTestCaseSection = false;
          break;
        }

        if (inTestCaseSection) {
          filteredLines.push(line);
        }
      }

      return filteredLines.join('\n');
    },

    // 解析表格格式的测试用例（参考AutoGenTestCase的做法）
    parseTableFormat(content) {
      if (!content) return [];

      const lines = content.split('\n').filter(line => line.trim());
      const worksheetData = [];

      for (let line of lines) {
        const trimmedLine = line.trim();

        // 检查是否是表格行（包含|分隔符，且不是分隔线）
        if (trimmedLine.includes('|') && !trimmedLine.includes('--------')) {
          const cells = trimmedLine.split('|').map(cell => cell.trim()).filter(cell => cell);
          if (cells.length > 1) {
            worksheetData.push(cells);
          }
        }
      }

      return worksheetData;
    },

    // 解析结构化格式的测试用例
    parseStructuredFormat(content) {
      if (!content) return [];

      const lines = content.split('\n').filter(line => line.trim());
      const worksheetData = [];

      // 添加表头
      worksheetData.push([
        this.$t('requirementAnalysis.excelTestCaseNumber'),
        this.$t('requirementAnalysis.excelTestScenario'),
        this.$t('requirementAnalysis.excelPrecondition'),
        this.$t('requirementAnalysis.excelTestSteps'),
        this.$t('requirementAnalysis.excelExpectedResult'),
        this.$t('requirementAnalysis.excelPriority')
      ]);

      let currentTestCase = {};
      let testCaseNumber = 1;
      let i = 0;

      while (i < lines.length) {
        const line = lines[i].trim();

        // 识别测试用例开始标志
        if (line.includes('测试用例') || line.includes('Test Case') ||
            line.match(/^(\d+\.|\*|\-|\d+、)/)) {

          // 如果之前有测试用例数据，先保存
          if (Object.keys(currentTestCase).length > 0) {
            worksheetData.push([
              currentTestCase.number || `TC${testCaseNumber}`,
              currentTestCase.scenario || '',
              currentTestCase.precondition || '',
              currentTestCase.steps || '',
              currentTestCase.expected || '',
              currentTestCase.priority || '中'
            ]);
            testCaseNumber++;
          }

          // 开始新的测试用例
          currentTestCase = {
            number: `TC${testCaseNumber}`,
            scenario: line.replace(/^(\d+\.|\*|\-|\d+、)\s*/, '').replace(/测试用例\d*[:：]?\s*/, ''),
            precondition: '',
            steps: '',
            expected: '',
            priority: '中'
          };
          i++;
        }
        // 识别前置条件
        else if (line.includes('前置条件') || line.includes('前提') ||
            line.includes('Precondition')) {
          let precondition = line.replace(/.*?[:：]\s*/, '');
          // 收集后续的前置条件行
          i++;
          while (i < lines.length) {
            const nextLine = lines[i].trim();
            if (nextLine.includes('测试步骤') || nextLine.includes('操作步骤') ||
                nextLine.includes('Test Steps') || nextLine.includes('步骤') ||
                nextLine.includes('预期结果') || nextLine.includes('Expected') ||
                nextLine.includes('优先级') || nextLine.includes('Priority') ||
                nextLine.includes('测试用例') || nextLine.includes('Test Case') ||
                nextLine.match(/^(\d+\.|\*|\-|\d+、)/)) {
              break;
            }
            if (nextLine) {
              precondition += '\n' + nextLine;
            }
            i++;
          }
          currentTestCase.precondition = precondition;
        }
        // 识别测试步骤
        else if (line.includes('测试步骤') || line.includes('操作步骤') ||
            line.includes('Test Steps') || line.includes('步骤')) {
          let steps = line.replace(/.*?[:：]\s*/, '');
          // 收集后续的步骤行
          i++;
          while (i < lines.length) {
            const nextLine = lines[i].trim();
            if (nextLine.includes('预期结果') || nextLine.includes('Expected') ||
                nextLine.includes('优先级') || nextLine.includes('Priority') ||
                nextLine.includes('测试用例') || nextLine.includes('Test Case') ||
                nextLine.match(/^(\d+\.|\*|\-|\d+、)/)) {
              break;
            }
            if (nextLine) {
              steps += '\n' + nextLine;
            }
            i++;
          }
          currentTestCase.steps = steps;
        }
        // 识别预期结果
        else if (line.includes('预期结果') || line.includes('Expected') ||
            line.includes('期望')) {
          let expected = line.replace(/.*?[:：]\s*/, '');
          // 收集后续的结果行
          i++;
          while (i < lines.length) {
            const nextLine = lines[i].trim();
            if (nextLine.includes('优先级') || nextLine.includes('Priority') ||
                nextLine.includes('测试用例') || nextLine.includes('Test Case') ||
                nextLine.match(/^(\d+\.|\*|\-|\d+、)/)) {
              break;
            }
            if (nextLine) {
              expected += '\n' + nextLine;
            }
            i++;
          }
          currentTestCase.expected = expected;
        }
        // 识别优先级
        else if (line.includes('优先级') || line.includes('Priority')) {
          currentTestCase.priority = line.replace(/.*?[:：]\s*/, '');
          i++;
        }
        // 如果是没有明确标识的行，可能是场景描述的延续
        else if (Object.keys(currentTestCase).length > 0 &&
            !currentTestCase.steps && !currentTestCase.expected &&
            !currentTestCase.precondition) {
          if (currentTestCase.scenario && line.length > 5) {
            currentTestCase.scenario += '\n' + line;
          }
          i++;
        } else {
          i++;
        }
      }

      // 保存最后一个测试用例
      if (Object.keys(currentTestCase).length > 0) {
        worksheetData.push([
          currentTestCase.number || `TC${testCaseNumber}`,
          currentTestCase.scenario || '',
          currentTestCase.precondition || '',
          currentTestCase.steps || '',
          currentTestCase.expected || '',
          currentTestCase.priority || '中'
        ]);
      }

      // 如果没有解析到结构化数据，则按原格式输出
      if (worksheetData.length <= 1) {
        worksheetData.length = 0; // 清空
        worksheetData.push([this.$t('requirementAnalysis.testCaseContent')]);
        content.split('\n').forEach((line, index) => {
          if (line.trim()) {
            worksheetData.push([line.trim()]);
          }
        });
      }

      return worksheetData;
    }
  }
}
</script>

<style scoped>
.requirement-analysis {
  padding: 20px 24px 32px;
  max-width: 1200px;
  margin: 0 auto;
  position: relative;
}

.page-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-card {
  background: var(--th-bg-elevated);
  border-radius: var(--th-radius-lg);
  padding: 24px;
  box-shadow: var(--th-shadow-xs);
  border: 1px solid var(--th-border);
}

.section-title {
  font-size: 1.125rem;
  color: var(--th-text-primary);
  margin: 0 0 8px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title-icon.output-icon {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%);
  flex-shrink: 0;
}

.panel-emoji {
  font-size: 1.1rem;
  line-height: 1;
}

.section-desc {
  color: #8c8c8c;
  font-size: 0.875rem;
  margin: 0 0 20px;
  line-height: 1.5;
}

/* 配置引导弹出窗口 */
.modal-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  background: rgba(15, 23, 42, 0.6) !important;
  backdrop-filter: blur(4px);
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  z-index: 9999 !important;
  padding: 20px;
  margin: 0 !important;
  opacity: 1 !important;
}

.guide-config-modal {
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%) !important;
  border-radius: 24px;
  padding: 36px;
  max-width: 850px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(226, 232, 240, 0.8);
  position: relative;
  flex-shrink: 0;
  margin: auto;
  opacity: 1 !important;
}

.guide-config-modal::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 5px;
  background: linear-gradient(90deg, #6c5ce7 0%, #8b7cf0 100%);
  border-radius: 24px 24px 0 0;
}

.guide-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 28px;
}

.guide-icon {
  width: 56px;
  height: 56px;
  flex-shrink: 0;
  filter: drop-shadow(0 4px 8px rgba(245, 158, 11, 0.2));
}

.guide-title h2 {
  font-size: 1.6rem;
  color: #1a202c;
  margin: 0 0 6px 0;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.guide-title p {
  color: #64748b;
  font-size: 0.95rem;
  margin: 0;
  font-weight: 400;
}

.config-groups {
  margin-bottom: 24px;
}

.config-group {
  margin-bottom: 20px;
}

.group-label {
  font-size: 0.85rem;
  color: #94a3b8;
  margin-bottom: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.config-items-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.config-item-inline {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-radius: 12px;
  border: 2px solid transparent;
  position: relative;
  overflow: hidden;
  font-weight: 500;
}

.config-item-inline::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: 12px 0 0 12px;
}

.config-item-inline.optional {
  opacity: 0.75;
}

/* 根据状态设置背景色和样式 */
.config-item-inline.status-enabled {
  background: linear-gradient(135deg, rgba(236, 253, 245, 0.9) 0%, rgba(220, 252, 231, 0.6) 100%);
  border-color: rgba(34, 197, 94, 0.2);
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.1);
}

.config-item-inline.status-enabled::before {
  background: linear-gradient(180deg, #22c55e 0%, #16a34a 100%);
}

.config-item-inline.status-disabled {
  background: linear-gradient(135deg, rgba(254, 249, 195, 0.9) 0%, rgba(254, 240, 138, 0.6) 100%);
  border-color: rgba(234, 179, 8, 0.2);
  box-shadow: 0 4px 12px rgba(234, 179, 8, 0.1);
}

.config-item-inline.status-disabled::before {
  background: linear-gradient(180deg, #eab308 0%, #ca8a04 100%);
}

.config-item-inline.status-unconfigured {
  background: linear-gradient(135deg, rgba(254, 242, 242, 0.9) 0%, rgba(254, 226, 226, 0.6) 100%);
  border-color: rgba(239, 68, 68, 0.2);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.1);
}

.config-item-inline.status-unconfigured::before {
  background: linear-gradient(180deg, #ef4444 0%, #dc2626 100%);
}

.status-symbol {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  font-size: 20px;
}

.config-label {
  font-size: 0.95rem;
  color: #334155;
  font-weight: 600;
  flex-shrink: 0;
}

.config-name {
  font-size: 0.85rem;
  color: #64748b;
  margin-left: 4px;
  font-weight: 500;
}

.status-text {
  margin-left: auto;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 700;
  background: #ef4444;
  color: white;
  white-space: nowrap;
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.2);
}

.status-text.warning {
  background: #eab308;
  box-shadow: 0 2px 6px rgba(234, 179, 8, 0.2);
}

.guide-actions {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  gap: 12px;
  margin-top: 30px;
  width: 100%;
}

.guide-actions button {
  flex: none !important;
  width: 240px !important;
  height: 50px !important;
  padding: 0 24px !important;
  border-radius: 12px;
  font-size: 0.95rem;
  font-weight: 600;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center;
  white-space: nowrap;
  opacity: 1 !important;
  cursor: pointer;
  box-sizing: border-box !important;
}

.guide-actions .generate-manual-btn {
  background: linear-gradient(135deg, #6c5ce7 0%, #5a4bd1 100%) !important;
  color: white !important;
  border: 2px solid transparent !important;
  box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
}

.guide-actions .skip-action {
  font-size: 0.85rem;
  color: #94a3b8;
  cursor: pointer;
  text-decoration: none;
  padding: 4px 8px;
  transition: color 0.3s;
}

.guide-actions .skip-action:hover {
  color: #64748b;
  text-decoration: underline;
}


.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #374151;
  font-size: 0.9rem;
}

/* 输出模式选择器 */
.output-mode-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  align-items: stretch;
}

.mode-option {
  position: relative;
  cursor: pointer;
  display: flex;
}

.mode-option input[type="radio"] {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.mode-content {
  border: 1.5px solid var(--th-border);
  border-radius: var(--th-radius-md);
  padding: 18px 20px;
  transition: all 0.2s ease;
  background: var(--th-bg-elevated);
  display: flex;
  align-items: flex-start;
  gap: 14px;
  width: 100%;
  box-sizing: border-box;
  min-height: 88px;
}

.mode-icon {
  font-size: 1.35rem;
  line-height: 1;
  flex-shrink: 0;
  margin-top: 2px;
}

.mode-text {
  flex: 1;
  min-width: 0;
}

.mode-option:hover .mode-content {
  border-color: var(--th-color-primary-light);
}

.mode-option.active .mode-content {
  border-color: var(--th-color-primary);
  background: var(--th-color-primary-softer);
  box-shadow: 0 0 0 1px var(--th-color-primary-soft);
}

.mode-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--th-text-primary);
  margin-bottom: 6px;
}

.mode-desc {
  font-size: 0.8rem;
  color: var(--th-text-secondary);
  line-height: 1.45;
}

.mode-option.active .mode-title {
  color: var(--th-color-primary);
}

.mode-option.active .mode-desc {
  color: var(--th-text-regular);
}

/* 需求来源卡片 */
.source-type-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.source-card {
  background: var(--th-bg-elevated);
  border: 1.5px solid var(--th-border);
  border-radius: var(--th-radius-md);
  padding: 20px 16px 18px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: var(--th-shadow-xs);
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 168px;
  font: inherit;
  color: inherit;
}

.source-card:hover {
  border-color: var(--th-color-primary-light);
  box-shadow: var(--th-shadow-sm);
  transform: translateY(-2px);
}

.source-card.active {
  border-color: var(--th-color-primary);
  background: var(--th-color-primary-softer);
  box-shadow: 0 0 0 1px var(--th-color-primary-soft), var(--th-shadow-sm);
}

.source-card-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--th-text-primary);
  margin-bottom: 14px;
  line-height: 1.35;
}

.source-card.active .source-card-title {
  color: var(--th-color-primary);
}

.source-card-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  margin-bottom: 14px;
  background: #f5f7fa;
}

.source-card-icon.manual {
  background: linear-gradient(145deg, #fff7e6, #ffe7ba);
}

.source-card-icon.upload {
  background: linear-gradient(145deg, #e6f4ff, #bae0ff);
}

.source-card-icon.knowledge {
  background: linear-gradient(145deg, #f6ffed, #d9f7be);
}

.source-card-icon.figma {
  background: linear-gradient(145deg, #fff0f6, #ffd6e7);
}

.source-card-icon.feishu {
  background: linear-gradient(145deg, #e6f4ff, #bae0ff);
}

.source-card-desc {
  margin: 0;
  font-size: 0.75rem;
  color: #8c8c8c;
  line-height: 1.5;
  text-align: center;
}

/* 知识库表单 */
.kb-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px 20px;
}

.kb-empty-hint {
  margin: 8px 0 0;
  font-size: 0.85rem;
  color: #64748b;
  line-height: 1.5;
}

.kb-empty-hint a {
  color: #1677ff;
  text-decoration: none;
}

.kb-empty-hint a:hover {
  text-decoration: underline;
}

.kb-search-settings {
  display: grid;
  grid-template-columns: 1.4fr 1.2fr 0.7fr 1.2fr;
  gap: 16px 20px;
  align-items: end;
  margin-bottom: 4px;
}

.search-type-group {
  display: flex;
  gap: 0;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  overflow: hidden;
  width: fit-content;
  max-width: 100%;
}

.search-type-btn {
  border: none;
  background: #fff;
  color: #595959;
  padding: 8px 14px;
  font-size: 0.85rem;
  cursor: pointer;
  border-right: 1px solid #d9d9d9;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.search-type-btn:last-child {
  border-right: none;
}

.search-type-btn:hover {
  color: #1677ff;
}

.search-type-btn.active {
  background: #1677ff;
  color: #fff;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.form-slider {
  flex: 1;
  accent-color: #1677ff;
  height: 4px;
  cursor: pointer;
}

.slider-value {
  min-width: 42px;
  font-size: 0.875rem;
  color: #1677ff;
  font-weight: 600;
  text-align: right;
}

.form-input-sm {
  max-width: 88px;
}

.kb-search-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.kb-search-row .form-input {
  flex: 1;
}

.kb-search-btn {
  flex-shrink: 0;
  min-width: 88px;
  height: 42px;
  border: none;
  border-radius: 6px;
  background: #1677ff;
  color: #fff;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease;
}

.kb-search-btn:hover:not(:disabled) {
  background: #4096ff;
}

.kb-search-btn:disabled {
  background: #d9d9d9;
  color: #fff;
  cursor: not-allowed;
}

/* Figma 解析面板 */
.figma-panel .section-title {
  margin-bottom: 12px;
}

.figma-panel .section-desc {
  margin: 0 0 16px;
  font-size: 0.875rem;
  color: #6b7280;
}

.parse-link-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.parse-link-row .form-input {
  flex: 1;
}

.parse-btn {
  flex-shrink: 0;
  min-width: 96px;
  height: 42px;
  border: none;
  border-radius: 6px;
  background: #1677ff;
  color: #fff;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease;
  padding: 0 16px;
}

.parse-btn:hover:not(:disabled) {
  background: #4096ff;
}

.parse-btn:disabled {
  background: #d9d9d9;
  color: #fff;
  cursor: not-allowed;
}

.figma-options-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 24px;
  margin: 4px 0 20px;
}

.figma-radio,
.figma-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  color: #374151;
  cursor: pointer;
  user-select: none;
}

.figma-radio input[type="radio"],
.figma-checkbox input[type="checkbox"] {
  width: 16px;
  height: 16px;
  margin: 0;
  accent-color: #1677ff;
  cursor: pointer;
}

.figma-project-group {
  margin-bottom: 0;
}

.feishu-panel .section-desc {
  margin: 0 0 16px;
  font-size: 0.875rem;
  color: #6b7280;
  line-height: 1.5;
}

.feishu-oauth-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
}

.feishu-oauth-status {
  font-size: 0.9rem;
  color: #166534;
  font-weight: 500;
  margin-right: auto;
}

.feishu-oauth-primary,
.feishu-oauth-secondary {
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 0.875rem;
  cursor: pointer;
}

.feishu-oauth-primary {
  background: #1677ff;
  color: #fff;
}

.feishu-oauth-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.feishu-oauth-secondary {
  background: #fff;
  color: #374151;
  border: 1px solid #d1d5db;
}

.feishu-preview {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.feishu-content-preview {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.875rem;
  line-height: 1.55;
  min-height: 200px;
}

@media (max-width: 768px) {
  .parse-link-row {
    flex-direction: column;
    align-items: stretch;
  }

  .figma-options-row {
    gap: 14px;
  }
}

.form-input, .form-select, .form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 0.9rem;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  background: #fff;
  color: #1f2937;
  box-sizing: border-box;
}

.form-input:focus, .form-select:focus, .form-textarea:focus {
  outline: none;
  border-color: #1677ff;
  box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.12);
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
}

.char-count {
  text-align: right;
  font-size: 0.8rem;
  color: #8c8c8c;
  margin-top: 5px;
}

.required {
  color: #ff4d4f;
}

.generate-manual-btn, .generate-btn {
  background: #1677ff;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: background 0.2s ease;
  width: 100%;
  margin-top: 10px;
}

.generate-manual-btn:hover:not(:disabled), .generate-btn:hover:not(:disabled) {
  background: #4096ff;
}

.generate-manual-btn:disabled, .generate-btn:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

.upload-area {
  border: 1.5px dashed #d9d9d9;
  border-radius: 10px;
  padding: 40px;
  text-align: center;
  transition: border-color 0.2s ease, background 0.2s ease;
  margin-bottom: 20px;
  background: #fafafa;
}

.upload-area.drag-over {
  border-color: #1677ff;
  background: #f0f7ff;
}

@media (max-width: 1100px) {
  .source-type-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .kb-search-settings {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .output-mode-selector,
  .source-type-grid,
  .kb-form-grid,
  .kb-search-settings {
    grid-template-columns: 1fr;
  }

  .kb-search-row {
    flex-direction: column;
    align-items: stretch;
  }

  .search-type-group {
    width: 100%;
  }

  .search-type-btn {
    flex: 1;
    padding: 8px 6px;
    font-size: 0.8rem;
  }
}

.upload-placeholder {
  color: #666;
}

.upload-icon {
  font-size: 3rem;
  margin-bottom: 15px;
  display: block;
}

.upload-hint {
  color: #999;
  font-size: 0.9rem;
  margin-top: 5px;
}

.select-file-btn {
  background: #1677ff;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  margin-top: 15px;
  transition: background 0.2s ease;
}

.select-file-btn:hover {
  background: #4096ff;
}

.file-selected {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 6px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.file-icon {
  font-size: 2rem;
}

.file-details {
  flex: 1;
}

.file-name {
  font-weight: 600;
  margin: 0;
}

.file-size {
  color: #666;
  font-size: 0.9rem;
  margin: 5px 0 0 0;
}

.remove-file {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
}

.generation-progress {
  margin: 40px 0;
}

.progress-card {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  border: 1px solid #eef0f3;
  text-align: center;
}

.progress-card h3 {
  color: #2c3e50;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}

.current-mode-badge {
  display: inline-block;
  background: #1677ff;
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 500;
  margin-left: 8px;
  box-shadow: 0 2px 8px rgba(22, 119, 255, 0.25);
}

.progress-info {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin-bottom: 30px;
  flex-wrap: wrap;
}

.progress-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.progress-item .label {
  font-size: 0.9rem;
  color: #666;
}

.progress-item .value {
  font-weight: 600;
  color: #2c3e50;
}

/* 流式内容显示区域 */
.stream-content-display {
  margin: 20px 0;
  border: 2px solid #e1e8ed;
  border-radius: 8px;
  overflow: hidden;
  background: #f8f9fa;
}

.stream-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #e9ecef;
  border-bottom: 1px solid #dee2e6;
}

.stream-title {
  font-weight: 600;
  color: #495057;
  font-size: 0.95rem;
}

.stream-status {
  font-size: 0.85rem;
  color: #6c757d;
  background: white;
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid #dee2e6;
}

.stream-content {
  max-height: 400px;
  overflow-y: auto;
  padding: 16px;
  text-align: left;
  background: white;
  font-size: 0.9rem;
  line-height: 1.6;
  color: #2c3e50;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.stream-content::-webkit-scrollbar {
  width: 8px;
}

.stream-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.stream-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.stream-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 最终版用例特殊样式 */
.stream-content.final-testcases {
  background: #f0f7ff;
  border-left: 4px solid #2196F3;
}

.stream-content.final-testcases::before {
  content: '📋 最终版本';
  display: block;
  font-weight: 600;
  color: #2196F3;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid #e3f2fd;
}

/* 流式输出指示器 */
.streaming-indicator {
  font-size: 0.85em;
  margin-left: 8px;
  color: #4CAF50;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.stream-content h1,
.stream-content h2,
.stream-content h3,
.stream-content h4,
.stream-content h5,
.stream-content h6 {
  margin-top: 1em;
  margin-bottom: 0.5em;
  color: #2c3e50;
  font-weight: 600;
}

.stream-content code {
  background: #f1f3f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
}

.stream-content pre {
  background: #f1f3f5;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 10px 0;
}

.stream-content pre code {
  background: none;
  padding: 0;
}

.progress-steps {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-bottom: 30px;
  flex-wrap: wrap;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  opacity: 0.4;
  transition: opacity 0.3s ease;
}

.step.active {
  opacity: 1;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #ddd;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: white;
}

.step.active .step-number {
  background: #3498db;
}

.step-text {
  font-size: 0.9rem;
  color: #666;
}

.cancel-generation-btn {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
}

.completion-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  flex-wrap: wrap;
}

.completion-actions button {
  flex: 1;
  min-width: 150px;
  padding: 12px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.completion-actions .download-btn {
  background: #28a745;
  color: white;
  font-size: 1rem;
}

.completion-actions .download-btn:hover {
  background: #218838;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(40, 167, 69, 0.3);
}

.completion-actions .save-btn {
  background: #007bff;
  color: white;
  font-size: 1rem;
}

.completion-actions .save-btn:hover {
  background: #0056b3;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 123, 255, 0.3);
}

.completion-actions .new-generation-btn {
  background: #6c757d;
  color: white;
  font-size: 1rem;
}

.completion-actions .new-generation-btn:hover {
  background: #5a6268;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(108, 117, 125, 0.3);
}

.generation-result {
  margin: 40px 0;
}

.result-header {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e1e8ed;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}

.result-header h2 {
  color: #27ae60;
  margin: 0;
}

.result-summary {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.summary-item {
  color: #666;
  font-size: 0.9rem;
}

.new-generation-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
}

.generated-testcases-section, .review-feedback-section, .final-testcases-section {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e1e8ed;
  margin-bottom: 20px;
}

.generated-testcases-section h3, .review-feedback-section h3, .final-testcases-section h3 {
  color: #2c3e50;
  margin-bottom: 20px;
}

.testcase-content, .review-content {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 20px;
  border-left: 4px solid #3498db;
}

.testcase-content pre, .review-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.9rem;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .result-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .progress-info, .result-summary {
    flex-direction: column;
    gap: 10px;
  }

  .progress-steps {
    gap: 10px;
  }
}

.actions-section {
  display: flex;
  gap: 20px;
  justify-content: center;
  margin-top: 30px;
  flex-wrap: wrap;
}

.download-btn, .save-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
}

.download-btn {
  background-color: #1abc9c;
  color: white;
}

.download-btn:hover {
  background-color: #16a085;
}

.save-btn {
  background-color: #3498db;
  color: white;
}

.save-btn:hover {
  background-color: #2980b9;
}

@media (max-width: 768px) {
  .actions-section {
    flex-direction: column;
    align-items: center;
  }

  .download-btn, .save-btn {
    width: 100%;
    max-width: 300px;
    justify-content: center;
  }
}
</style>

<style>
/* 全局样式：确保弹窗不受任何容器限制 */
.modal-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  max-width: none !important;
  max-height: none !important;
  background: rgba(15, 23, 42, 0.6) !important;
  backdrop-filter: blur(4px);
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  z-index: 9999 !important;
  padding: 20px;
  margin: 0 !important;
  opacity: 1 !important;
  box-sizing: border-box !important;
}

.guide-config-modal {
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%) !important;
  border-radius: 24px;
  padding: 36px;
  max-width: 850px !important;
  width: 100% !important;
  min-width: 300px !important;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(226, 232, 240, 0.8);
  position: relative;
  flex-shrink: 0;
  margin: auto;
  opacity: 1 !important;
  box-sizing: border-box !important;
}

/* 全局按钮样式 */
.guide-actions {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  gap: 12px;
  margin-top: 30px;
  width: 100%;
}

.guide-actions button {
  flex: none !important;
  width: 240px !important;
  height: 50px !important;
  padding: 0 24px !important;
  border-radius: 12px;
  font-size: 0.95rem;
  font-weight: 600;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center;
  white-space: nowrap;
  opacity: 1 !important;
  box-sizing: border-box !important;
  cursor: pointer;
}

.guide-actions .generate-manual-btn {
  background: linear-gradient(135deg, #6c5ce7 0%, #5a4bd1 100%) !important;
  color: white !important;
  border: 2px solid transparent !important;
  box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
}

.guide-actions .skip-action {
  font-size: 0.85rem;
  color: #94a3b8;
  cursor: pointer;
  text-decoration: none;
  padding: 4px 8px;
  transition: color 0.3s;
}

.guide-actions .skip-action:hover {
  color: #64748b;
  text-decoration: underline;
}
</style>