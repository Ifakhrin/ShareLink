// ShareLink - Global Utilities & Confirmations

document.addEventListener('DOMContentLoaded', () => {
    // Mobile Hamburger Navbar Toggle
    const navToggleBtn = document.getElementById('navToggleBtn');
    const navLinks = document.querySelector('.nav-links');

    if (navToggleBtn && navLinks) {
        navToggleBtn.addEventListener('click', () => {
            navLinks.classList.toggle('open');
            navToggleBtn.classList.toggle('active');
        });
    }

    // Copy transfer code helper
    const copyCodeBtn = document.getElementById('copyCodeBtn');
    const transferCodeElement = document.getElementById('transferCodeText');

    if (copyCodeBtn && transferCodeElement) {
        copyCodeBtn.addEventListener('click', () => {
            const code = transferCodeElement.textContent.trim();
            navigator.clipboard.writeText(code).then(() => {
                const originalText = copyCodeBtn.textContent;
                copyCodeBtn.textContent = 'Kode Tersalin!';
                copyCodeBtn.classList.add('btn-primary');
                setTimeout(() => {
                    copyCodeBtn.textContent = originalText;
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy code: ', err);
            });
        });
    }

    // Confirmation dialog for forms with data-confirm attribute
    document.querySelectorAll('form[data-confirm]').forEach(form => {
        form.addEventListener('submit', (e) => {
            const message = form.getAttribute('data-confirm') || 'Apakah Anda yakin ingin melanjutkan tindakan ini?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
});
