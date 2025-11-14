// ChatGPT-style PDF upload
import { buildBackendUrl } from '../backendConfig.js';

let currentPdfAttachment = null;

export function createPdfUploadButton() {
  // Hidden file input
  const fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.accept = '.pdf';
  fileInput.style.display = 'none';
  fileInput.id = 'pdfFileInput';

  // Paperclip button
  const button = document.createElement('button');
  button.className = 'pdf-upload-button';
  button.title = 'Attach PDF';
  button.innerHTML = '📎';

  // Click to upload
  button.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
      await uploadPdf(file);
    }
    // Reset input so same file can be selected again
    fileInput.value = '';
  });

  const container = document.createElement('div');
  container.className = 'pdf-upload-container';
  container.appendChild(button);
  container.appendChild(fileInput);

  return container;
}

export function createPdfAttachmentCard() {
  const card = document.createElement('div');
  card.id = 'pdfAttachmentCard';
  card.className = 'pdf-attachment-card';
  card.style.display = 'none';

  return card;
}

function showPdfAttachment(pdfData) {
  currentPdfAttachment = pdfData;

  const card = document.getElementById('pdfAttachmentCard');
  if (!card) return;

  card.innerHTML = '';
  card.style.display = 'flex';

  // PDF icon
  const icon = document.createElement('div');
  icon.className = 'pdf-attachment-icon';
  icon.innerHTML = '📄';

  // File info
  const info = document.createElement('div');
  info.className = 'pdf-attachment-info';

  const name = document.createElement('div');
  name.className = 'pdf-attachment-name';
  name.textContent = pdfData.original_name;

  const meta = document.createElement('div');
  meta.className = 'pdf-attachment-meta';
  const sizeText =
    pdfData.size_kb < 1024
      ? `${pdfData.size_kb} KB`
      : `${(pdfData.size_kb / 1024).toFixed(1)} MB`;
  meta.textContent = pdfData.pages
    ? `${pdfData.pages} pages • ${sizeText}`
    : sizeText;

  info.appendChild(name);
  info.appendChild(meta);

  // Remove button
  const removeBtn = document.createElement('button');
  removeBtn.className = 'pdf-attachment-remove';
  removeBtn.innerHTML = '×';
  removeBtn.title = 'Remove';
  removeBtn.onclick = removePdfAttachment;

  card.appendChild(icon);
  card.appendChild(info);
  card.appendChild(removeBtn);
}

function removePdfAttachment() {
  currentPdfAttachment = null;
  const card = document.getElementById('pdfAttachmentCard');
  if (card) {
    card.style.display = 'none';
    card.innerHTML = '';
  }
}

async function uploadPdf(file) {
  const formData = new FormData();
  formData.append('pdf', file);

  try {
    const response = await fetch(buildBackendUrl('/api/upload_pdf/'), {
      method: 'POST',
      body: formData,
    });

    const result = await response.json();

    if (result.success) {
      // Show the PDF attachment card
      showPdfAttachment(result);
    } else {
      showError(result.error || 'Upload failed');
    }
  } catch (error) {
    showError(`Upload error: ${error.message}`);
  }
}

function showError(message) {
  const respons = document.getElementById('respons');
  if (respons) {
    const msg = document.createElement('div');
    msg.className = 'system-message error';
    msg.textContent = message;
    respons.appendChild(msg);

    // Auto scroll to bottom
    const content = document.getElementById('content');
    if (content) {
      content.scrollTop = content.scrollHeight;
    }
  }
}

export function getCurrentPdfAttachment() {
  return currentPdfAttachment;
}
