/* ========================================
   MultiTion Education — Main JavaScript
   ======================================== */

document.addEventListener('DOMContentLoaded', function () {

    // ==================== THEME TOGGLE ====================
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;
    const savedTheme = localStorage.getItem('multition-theme') || 'light';
    html.setAttribute('data-theme', savedTheme);
    if (themeToggle) themeToggle.textContent = savedTheme === 'dark' ? '☀️' : '🌙';

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const current = html.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', next);
            localStorage.setItem('multition-theme', next);
            themeToggle.textContent = next === 'dark' ? '☀️' : '🌙';
        });
    }

    // ==================== SIDEBAR TOGGLE (Dashboard) ====================
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('dashboardSidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    function openSidebar() {
        if (sidebar) sidebar.classList.add('open');
        if (sidebarOverlay) sidebarOverlay.classList.add('active');
    }
    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('open');
        if (sidebarOverlay) sidebarOverlay.classList.remove('active');
    }
    if (sidebarToggle) sidebarToggle.addEventListener('click', openSidebar);
    if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeSidebar);

    // ==================== NOTIFICATION DROPDOWN ====================
    const notifBell = document.getElementById('notifBell');
    const notifDropdown = document.getElementById('notifDropdown');
    const notifBadge = document.getElementById('notifBadge');
    const notifBody = document.getElementById('notifDropdownBody');

    if (notifBell && notifDropdown) {
        notifBell.addEventListener('click', (e) => {
            e.stopPropagation();
            notifDropdown.classList.toggle('show');
            if (notifDropdown.classList.contains('show')) {
                fetchNotifications();
            }
        });

        document.addEventListener('click', (e) => {
            if (!notifDropdown.contains(e.target) && e.target !== notifBell) {
                notifDropdown.classList.remove('show');
            }
        });
    }

    function fetchNotifications() {
        fetch('/notifications/api/', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(r => r.json())
        .then(data => {
            // Update badge
            if (notifBadge) {
                if (data.unread_count > 0) {
                    notifBadge.textContent = data.unread_count;
                    notifBadge.style.display = 'flex';
                } else {
                    notifBadge.style.display = 'none';
                }
            }

            // Render notifications
            if (notifBody) {
                if (data.notifications.length === 0) {
                    notifBody.innerHTML = '<div class="empty-state" style="padding:2rem"><p>No notifications yet</p></div>';
                } else {
                    notifBody.innerHTML = data.notifications.map(n => `
                        <a href="${n.link || '/notifications/' + n.id + '/read/'}" class="notif-item ${n.is_read ? '' : 'unread'}">
                            <span class="notif-dot ${n.type}"></span>
                            <div style="flex:1;min-width:0">
                                <div style="font-weight:${n.is_read ? '400' : '600'};font-size:0.85rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${n.title}</div>
                                <div style="font-size:0.78rem;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${n.message}</div>
                                <div style="font-size:0.72rem;color:var(--text-muted);margin-top:2px">${n.time_ago}</div>
                            </div>
                        </a>
                    `).join('');
                }
            }
        })
        .catch(err => {
            console.log('Notification fetch error:', err);
        });
    }

    // Poll notifications every 30 seconds
    if (notifBell) {
        fetchNotifications();
        setInterval(() => {
            fetch('/notifications/api/', {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(r => r.json())
            .then(data => {
                if (notifBadge) {
                    if (data.unread_count > 0) {
                        notifBadge.textContent = data.unread_count;
                        notifBadge.style.display = 'flex';
                    } else {
                        notifBadge.style.display = 'none';
                    }
                }
            })
            .catch(() => {});
        }, 30000);
    }

    // ==================== COOKIE CONSENT ====================
    const cookieBanner = document.getElementById('cookieBanner');
    if (cookieBanner && !localStorage.getItem('multition-cookie-consent')) {
        setTimeout(() => {
            cookieBanner.classList.add('show');
        }, 1500);
    }

    // ==================== TOAST AUTO-DISMISS ====================
    document.querySelectorAll('.alert-custom').forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-20px)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    // ==================== SMOOTH SCROLL FOR ANCHOR LINKS ====================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ==================== FORM ENHANCEMENTS ====================
    // Add focus styles to form inputs
    document.querySelectorAll('.form-control, .form-select').forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });
    });

    // ==================== MOBILE NAV ====================
    const navToggler = document.querySelector('.navbar-toggler');
    if (navToggler) {
        navToggler.addEventListener('click', function() {
            const icon = this.querySelector('.navbar-toggler-icon');
            this.classList.toggle('collapsed');
        });
    }

    // ==================== DROPDOWN FIX FOR THEME ====================
    document.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.background = 'var(--bg-secondary)';
        });
        item.addEventListener('mouseleave', function() {
            this.style.background = 'transparent';
        });
    });

});

// ==================== COOKIE FUNCTIONS (Global) ====================
function acceptCookies() {
    localStorage.setItem('multition-cookie-consent', 'accepted');
    const banner = document.getElementById('cookieBanner');
    if (banner) {
        banner.classList.remove('show');
        setTimeout(() => banner.style.display = 'none', 300);
    }
    // Also notify server
    fetch('/accounts/cookie-consent/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ consent: true })
    }).catch(() => {});
}

function declineCookies() {
    localStorage.setItem('multition-cookie-consent', 'declined');
    const banner = document.getElementById('cookieBanner');
    if (banner) {
        banner.classList.remove('show');
        setTimeout(() => banner.style.display = 'none', 300);
    }
}

function getCookie(name) {
    let value = null;
    document.cookie.split(';').forEach(c => {
        c = c.trim();
        if (c.startsWith(name + '=')) {
            value = c.substring(name.length + 1);
        }
    });
    return value;
}
