/**
 * PDF Layout-Preserving Translator Frontend Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const uploadPrompt = document.getElementById('uploadPrompt');
  const fileInfo = document.getElementById('fileInfo');
  const fileNameDisplay = document.getElementById('fileName');
  const fileSizeDisplay = document.getElementById('fileSize');
  const removeFileBtn = document.getElementById('removeFileBtn');
  
  const targetLangSelect = document.getElementById('targetLang');
  const translateBtn = document.getElementById('translateBtn');
  const translateBtnText = document.getElementById('translateBtnText');
  const translateSpinner = document.getElementById('translateSpinner');
  
  const progressSection = document.getElementById('progressSection');
  const progressBarFill = document.getElementById('progressBarFill');
  const progressPercent = document.getElementById('progressPercent');
  const progressStatusText = document.getElementById('progressStatusText');
  const progressPageText = document.getElementById('progressPageText');
  
  const downloadSection = document.getElementById('downloadSection');
  const downloadBtn = document.getElementById('downloadBtn');
  const resetBtn = document.getElementById('resetBtn');
  
  const errorAlert = document.getElementById('errorAlert');
  const errorMessage = document.getElementById('errorMessage');

  let selectedFile = null;
  let currentJobId = null;
  let pollInterval = null;

  // File Drag & Drop Event Listeners
  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    }, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    }, false);
  });

  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files && files.length > 0) {
      handleFileSelected(files[0]);
    }
  });

  dropzone.addEventListener('click', (e) => {
    if (e.target !== fileInput && (!removeFileBtn || !removeFileBtn.contains(e.target))) {
      fileInput.click();
    }
  });

  fileInput.addEventListener('click', (e) => {
    e.stopPropagation();
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  removeFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    resetFileSelection();
  });

  function handleFileSelected(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      showError('Invalid file type. Please upload a PDF document (.pdf).');
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      showError('File size exceeds the 25MB limit. Please select a smaller PDF.');
      return;
    }

    selectedFile = file;
    hideError();

    fileNameDisplay.textContent = file.name;
    fileSizeDisplay.textContent = formatBytes(file.size);

    if (uploadPrompt) uploadPrompt.classList.add('hidden');
    fileInfo.classList.remove('hidden');
    dropzone.classList.add('border-indigo-500', 'bg-indigo-950/20');
    translateBtn.disabled = false;
    translateBtn.classList.remove('opacity-50', 'cursor-not-allowed');
  }

  function resetFileSelection() {
    selectedFile = null;
    fileInput.value = '';
    if (uploadPrompt) uploadPrompt.classList.remove('hidden');
    fileInfo.classList.add('hidden');
    dropzone.classList.remove('border-indigo-500', 'bg-indigo-950/20');
    translateBtn.disabled = true;
    translateBtn.classList.add('opacity-50', 'cursor-not-allowed');
  }

  // Translation Trigger
  translateBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    const targetLang = targetLangSelect.value;
    if (!targetLang) {
      showError('Please select a target language.');
      return;
    }

    hideError();
    setTranslatingState(true);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('target_lang', targetLang);

    try {
      const response = await fetch('/api/translate', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to initialize translation job.');
      }

      const data = await response.json();
      currentJobId = data.job_id;

      // Start progress polling
      startPollingProgress();

    } catch (err) {
      showError(err.message);
      setTranslatingState(false);
    }
  });

  function startPollingProgress() {
    progressSection.classList.remove('hidden');
    downloadSection.classList.add('hidden');
    
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
      if (!currentJobId) return;

      try {
        const res = await fetch(`/api/progress/${currentJobId}`);
        if (!res.ok) throw new Error('Could not fetch translation status.');

        const data = await res.json();

        // Update progress UI
        const pct = Math.min(100, Math.max(0, data.progress || 0));
        progressBarFill.style.width = `${pct}%`;
        progressPercent.textContent = `${pct}%`;
        progressStatusText.textContent = data.message || 'Processing pages...';

        if (data.total_pages > 0) {
          progressPageText.textContent = `Page ${data.current_page} of ${data.total_pages}`;
        } else {
          progressPageText.textContent = 'Analyzing PDF layout...';
        }

        if (data.status === 'completed') {
          clearInterval(pollInterval);
          setTranslatingState(false);
          progressSection.classList.add('hidden');
          downloadSection.classList.remove('hidden');
        } else if (data.status === 'failed') {
          clearInterval(pollInterval);
          setTranslatingState(false);
          progressSection.classList.add('hidden');
          showError(data.error || data.message || 'Translation failed.');
        }

      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 800);
  }

  // Download Trigger
  downloadBtn.addEventListener('click', () => {
    if (currentJobId) {
      window.location.href = `/api/download/${currentJobId}`;
    }
  });

  resetBtn.addEventListener('click', () => {
    currentJobId = null;
    resetFileSelection();
    downloadSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    hideError();
  });

  function setTranslatingState(isTranslating) {
    if (isTranslating) {
      translateBtn.disabled = true;
      translateBtnText.textContent = 'Translating Document...';
      translateSpinner.classList.remove('hidden');
    } else {
      translateBtn.disabled = selectedFile === null;
      translateBtnText.textContent = 'Translate Document';
      translateSpinner.classList.add('hidden');
    }
  }

  function showError(msg) {
    errorMessage.textContent = msg;
    errorAlert.classList.remove('hidden');
  }

  function hideError() {
    errorAlert.classList.add('hidden');
    errorMessage.textContent = '';
  }

  function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  // FAQ Accordion Toggles
  window.toggleFaq = function(index) {
    const content = document.getElementById(`faq-content-${index}`);
    const icon = document.getElementById(`faq-icon-${index}`);
    
    if (content.classList.contains('hidden')) {
      content.classList.remove('hidden');
      icon.style.transform = 'rotate(180deg)';
    } else {
      content.classList.add('hidden');
      icon.style.transform = 'rotate(0deg)';
    }
  };
});
