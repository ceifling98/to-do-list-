// Handles dark mode toggle, drag-and-drop, and checkbox toggling
// Requires: Tailwind CSS dark mode, Sortable.js, Heroicons CDN

window.toggleDarkMode = function(toggle) {
    const html = document.documentElement;
    if (toggle.checked) {
        html.classList.add('dark');
        localStorage.setItem('theme', 'dark');
    } else {
        html.classList.remove('dark');
        localStorage.setItem('theme', 'light');
    }
};

document.addEventListener('DOMContentLoaded', function() {
    // --- Dark mode toggle ---
    const darkToggle = document.getElementById('dark-toggle');
    const html = document.documentElement;
    // Load preference
    if (localStorage.getItem('theme') === 'dark' ||
        (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        html.classList.add('dark');
        if (darkToggle) darkToggle.checked = true;
    } else {
        html.classList.remove('dark');
        if (darkToggle) darkToggle.checked = false;
    }
    if (darkToggle) {
        darkToggle.addEventListener('change', function() {
            window.toggleDarkMode(this);
        });
    }

    // --- Dark mode toggle (Settings page support) ---
    // Listen for changes to localStorage from other tabs/pages
    window.addEventListener('storage', function(e) {
        if (e.key === 'theme') {
            if (e.newValue === 'dark') {
                html.classList.add('dark');
            } else {
                html.classList.remove('dark');
            }
        }
    });

    // --- Drag-and-drop sorting (Sortable.js) ---
    if (window.Sortable) {
        const list = document.getElementById('task-list');
        if (list) {
            new Sortable(list, {
                animation: 150,
                handle: '.drag-handle',
                onEnd: function(evt) {
                    // Optionally: send new order to backend
                    // let order = [...list.children].map(li => li.dataset.id);
                    // fetch('/reorder', {method:'POST', body: JSON.stringify({order})})
                }
            });
        }
    }

    // --- Checkbox toggle for tasks ---
    document.querySelectorAll('.task-checkbox').forEach(cb => {
        cb.addEventListener('change', function() {
            const taskId = this.dataset.id;
            if (this.checked) {
                fetch(`/complete/${taskId}`, {method: 'POST'}).then(() => location.reload());
            } else {
                fetch(`/uncomplete/${taskId}`, {method: 'POST'}).then(() => location.reload());
            }
        });
    });

    // --- Mobile nav open/close logic ---
    const navToggle = document.getElementById('nav-toggle');
    const mobileNav = document.getElementById('mobile-nav');
    const navClose = document.getElementById('nav-close');
    if (navToggle && mobileNav && navClose) {
        navToggle.addEventListener('click', function() {
            mobileNav.classList.remove('hidden');
        });
        navClose.addEventListener('click', function() {
            mobileNav.classList.add('hidden');
        });
        // Also close when clicking outside the drawer
        mobileNav.addEventListener('click', function(e) {
            if (e.target === mobileNav) mobileNav.classList.add('hidden');
        });
    }
});
