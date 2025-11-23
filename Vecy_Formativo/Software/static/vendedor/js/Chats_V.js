// Toggle business status
        document.getElementById('businessToggle').addEventListener('click', function() {
            const statusText = document.getElementById('statusText');
            const isActive = this.classList.toggle('active');
            
            statusText.textContent = isActive ? 'Abierto' : 'Cerrado';
            statusText.style.color = isActive ? '#10b981' : '#6b7280';
        });

        // Chat item selection
        document.querySelectorAll('.chat-item').forEach(item => {
            item.addEventListener('click', function() {
                document.querySelectorAll('.chat-item').forEach(i => i.classList.remove('active'));
                this.classList.add('active');
            });
        });

        // Auto-resize textarea
        const textarea = document.querySelector('.message-input');
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });