// ShareLink - Multi-File Upload, Subject/Message Character Counter & Preview Modal Handler

document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const dropzone = document.getElementById('dropzone');
    const fileListContainer = document.getElementById('fileListContainer');
    const selectedFilesTable = document.getElementById('selectedFilesTable');
    const totalFilesCount = document.getElementById('totalFilesCount');
    const totalFilesSize = document.getElementById('totalFilesSize');
    const previewBtn = document.getElementById('previewBtn');
    const clientError = document.getElementById('clientError');

    const subjectInput = document.getElementById('subjectInput');
    const subjectCounter = document.getElementById('subjectCounter');
    const messageInput = document.getElementById('messageInput');
    const messageCounter = document.getElementById('messageCounter');

    const previewModal = document.getElementById('previewModal');
    const previewReceiverName = document.getElementById('previewReceiverName');
    const previewSubjectText = document.getElementById('previewSubjectText');
    const previewMessageText = document.getElementById('previewMessageText');
    const previewAttachmentSummary = document.getElementById('previewAttachmentSummary');
    const closePreviewBtn = document.getElementById('closePreviewBtn');
    const confirmSubmitBtn = document.getElementById('confirmSubmitBtn');

    const progressContainer = document.querySelector('.progress-container');
    const progressBarFill = document.querySelector('.progress-bar-fill');
    const progressPercentText = document.getElementById('progressPercentText');

    if (!uploadForm || !fileInput || !dropzone) return;

    let selectedFiles = [];

    const MAX_FILE_SIZE = 1073741824; // 1 GB
    const MAX_TRANSFER_SIZE = 2147483648; // 2 GB

    function formatBytes(bytes) {
        if (bytes === 0) return '0 Byte';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Character Counter Handlers
    if (subjectInput && subjectCounter) {
        subjectInput.addEventListener('input', () => {
            const len = subjectInput.value.length;
            subjectCounter.textContent = `${len} / 150`;
            if (len > 150) {
                subjectCounter.style.color = 'var(--rose-accent)';
            } else {
                subjectCounter.style.color = 'var(--text-subtle)';
            }
            validateFormState();
        });
    }

    if (messageInput && messageCounter) {
        messageInput.addEventListener('input', () => {
            const len = messageInput.value.length;
            messageCounter.textContent = `${len} / 2000`;
            if (len > 2000) {
                messageCounter.style.color = 'var(--rose-accent)';
            } else {
                messageCounter.style.color = 'var(--text-subtle)';
            }
            validateFormState();
        });
    }

    function validateFormState() {
        const receiverSelect = document.getElementById('receiverSelect');
        const isReceiverValid = receiverSelect && receiverSelect.value !== '';
        const isSubjectValid = subjectInput && subjectInput.value.trim() !== '' && subjectInput.value.length <= 150;
        const isMessageValid = !messageInput || messageInput.value.length <= 2000;
        const isFilesValid = selectedFiles.length > 0;

        let totalSize = selectedFiles.reduce((acc, f) => acc + f.size, 0);
        let sizeOk = totalSize <= MAX_TRANSFER_SIZE && !selectedFiles.some(f => f.size === 0 || f.size > MAX_FILE_SIZE);

        if (previewBtn) {
            previewBtn.disabled = !(isReceiverValid && isSubjectValid && isMessageValid && isFilesValid && sizeOk);
        }
    }

    function renderFileList() {
        if (!selectedFilesTable) return;
        selectedFilesTable.innerHTML = '';
        clientError.style.display = 'none';

        if (selectedFiles.length === 0) {
            fileListContainer.style.display = 'none';
            validateFormState();
            return;
        }

        let totalSize = 0;
        let hasError = false;
        let errorMsg = '';

        selectedFiles.forEach((file, index) => {
            totalSize += file.size;
            const tr = document.createElement('tr');
            
            let fileError = '';
            if (file.size === 0) {
                fileError = 'File 0 Byte';
                hasError = true;
            } else if (file.size > MAX_FILE_SIZE) {
                fileError = 'Ukuran > 1 GB';
                hasError = true;
            }

            tr.innerHTML = `
                <td><strong>${escapeHtml(file.name)}</strong></td>
                <td>${formatBytes(file.size)}</td>
                <td>
                    ${fileError ? `<span class="status-badge status-FAILED">${fileError}</span>` : `<span class="status-badge status-AVAILABLE">Siap Unggah</span>`}
                </td>
                <td style="text-align: right;">
                    <button type="button" class="btn btn-danger btn-sm remove-file-btn" data-index="${index}">Hapus</button>
                </td>
            `;
            selectedFilesTable.appendChild(tr);
        });

        if (totalSize > MAX_TRANSFER_SIZE) {
            hasError = true;
            errorMsg = `Total ukuran file (${formatBytes(totalSize)}) melebihi batas 2 GB.`;
        }

        totalFilesCount.textContent = `${selectedFiles.length} file`;
        totalFilesSize.textContent = `${formatBytes(totalSize)} / 2 GB`;
        fileListContainer.style.display = 'block';

        if (hasError) {
            clientError.textContent = errorMsg || 'Salah satu atau beberapa file tidak memenuhi syarat batas ukuran.';
            clientError.style.display = 'block';
        }
        
        validateFormState();
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function handleFiles(files) {
        Array.from(files).forEach(file => {
            if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
                selectedFiles.push(file);
            }
        });
        renderFileList();
    }

    // Drag & Drop Listeners
    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    ['dragleave', 'dragend'].forEach(evt => {
        dropzone.addEventListener(evt, () => dropzone.classList.remove('dragover'));
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFiles(e.target.files);
        }
    });

    const receiverSelect = document.getElementById('receiverSelect');
    if (receiverSelect) {
        receiverSelect.addEventListener('change', validateFormState);
    }

    if (selectedFilesTable) {
        selectedFilesTable.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-file-btn')) {
                const idx = parseInt(e.target.getAttribute('data-index'), 10);
                selectedFiles.splice(idx, 1);
                renderFileList();
            }
        });
    }

    // Preview Modal Event Listeners
    if (previewBtn && previewModal) {
        previewBtn.addEventListener('click', () => {
            const selectedOpt = receiverSelect.options[receiverSelect.selectedIndex];
            const receiverName = selectedOpt ? selectedOpt.text : '-';
            const subjectVal = subjectInput.value.trim();
            const messageVal = messageInput ? messageInput.value.trim() : '';

            let totalSize = selectedFiles.reduce((acc, f) => acc + f.size, 0);

            previewReceiverName.textContent = receiverName;
            previewSubjectText.textContent = subjectVal || '(Tanpa Judul)';
            previewMessageText.textContent = messageVal || '(Tanpa Pesan Pengantar)';
            previewAttachmentSummary.textContent = `${selectedFiles.length} file • ${formatBytes(totalSize)}`;

            previewModal.showModal();
        });
    }

    if (closePreviewBtn && previewModal) {
        closePreviewBtn.addEventListener('click', () => previewModal.close());
    }

    if (confirmSubmitBtn) {
        confirmSubmitBtn.addEventListener('click', () => {
            if (previewModal) previewModal.close();
            executeFileUpload();
        });
    }

    // Actual XHR Upload Function
    function executeFileUpload() {
        const receiverSelectVal = receiverSelect ? receiverSelect.value : '';
        const subjectVal = subjectInput ? subjectInput.value.trim() : '';
        const messageVal = messageInput ? messageInput.value.trim() : '';

        if (!receiverSelectVal || !subjectVal || selectedFiles.length === 0) {
            clientError.textContent = 'Harap lengkapi penerima, judul, dan sekurangnya satu lampiran file.';
            clientError.style.display = 'block';
            return;
        }

        const formData = new FormData();
        formData.append('receiver_id', receiverSelectVal);
        formData.append('subject', subjectVal);
        formData.append('message', messageVal);

        selectedFiles.forEach(file => {
            formData.append('files', file);
        });

        const xhr = new XMLHttpRequest();
        xhr.open('POST', uploadForm.action, true);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                progressContainer.style.display = 'block';
                progressBarFill.style.width = percent + '%';
                progressPercentText.textContent = `Mengunggah... ${percent}% (${formatBytes(e.loaded)} dari ${formatBytes(e.total)})`;
            }
        });

        previewBtn.disabled = true;
        previewBtn.textContent = 'Mengunggah...';

        xhr.onload = function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const res = JSON.parse(xhr.responseText);
                    if (res.success && res.redirect_url) {
                        window.location.href = res.redirect_url;
                    } else {
                        clientError.textContent = res.error || 'Terjadi kesalahan saat mengunggah.';
                        clientError.style.display = 'block';
                        previewBtn.disabled = false;
                        previewBtn.textContent = 'Pratinjau & Kirim';
                    }
                } catch(err) {
                    window.location.href = xhr.responseURL || '/dashboard';
                }
            } else {
                let errText = 'Gagal mengunggah file. Silakan periksa ukuran file dan koneksi Anda.';
                try {
                    const res = JSON.parse(xhr.responseText);
                    if (res.error) errText = res.error;
                } catch(e) {}
                clientError.textContent = errText;
                clientError.style.display = 'block';
                previewBtn.disabled = false;
                previewBtn.textContent = 'Pratinjau & Kirim';
                progressContainer.style.display = 'none';
            }
        };

        xhr.onerror = function() {
            clientError.textContent = 'Terjadi kesalahan jaringan atau koneksi terputus saat mengunggah.';
            clientError.style.display = 'block';
            previewBtn.disabled = false;
            previewBtn.textContent = '👁️ Pratinjau & Kirim';
            progressContainer.style.display = 'none';
        };

        xhr.send(formData);
    }
});
