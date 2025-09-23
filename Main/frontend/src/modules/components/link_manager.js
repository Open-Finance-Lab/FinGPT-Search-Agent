export function createLinkManager() {
    // Container for the whole link manager
    const linkList = document.createElement('div');
    linkList.className = 'link-list';

    // Modal for delete confirmation
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'none';
    modal.innerHTML = `
      <div class="modal-content">
        <p>Are you sure you want to delete this link?</p>
        <div class="modal-buttons">
          <button class="confirm-btn">Delete</button>
          <button class="cancel-btn">Cancel</button>
        </div>
      </div>
    `;

    let linkToDelete = null;

    function createLinkInput() {
        const wrapper = document.createElement('div');
        wrapper.className = 'link-input';

        const btn = document.createElement('button');
        btn.className = 'plus-btn';
        btn.textContent = '+';

        const input = document.createElement('input');
        input.type = 'text';
        input.placeholder = 'Paste link...';

        wrapper.appendChild(btn);
        wrapper.appendChild(input);
        linkList.appendChild(wrapper);

        btn.addEventListener('click', () => {
            wrapper.classList.add('input-visible');
            input.focus();
        });

        input.addEventListener('blur', () => {
            if (input.value.trim() === '') {
                wrapper.classList.remove('input-visible');
            }
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const value = input.value.trim();
                if (value !== '') {
                    addLink(value, wrapper);
                    createLinkInput();
                }
            }
        });
    }

    function addLink(value, wrapper) {
        wrapper.innerHTML = `
          <div class="link-preview">
            <span>${value}</span>
            <button class="delete-btn" title="Delete Link">&times;</button>
          </div>
        `;

        const deleteBtn = wrapper.querySelector('.delete-btn');
        deleteBtn.addEventListener('click', () => {
            linkToDelete = wrapper;
            modal.style.display = 'block';
        });
    }

    // Modal logic
    modal.querySelector('.confirm-btn').addEventListener('click', () => {
        if (linkToDelete) {
            linkToDelete.remove();
            linkToDelete = null;
        }
        modal.style.display = 'none';
    });

    modal.querySelector('.cancel-btn').addEventListener('click', () => {
        modal.style.display = 'none';
        linkToDelete = null;
    });

    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
            linkToDelete = null;
        }
    });

    // Initialize
    createLinkInput();

    // Return both the link list and the modal
    const container = document.createElement('div');
    container.appendChild(linkList);
    container.appendChild(modal);

    return container;
}