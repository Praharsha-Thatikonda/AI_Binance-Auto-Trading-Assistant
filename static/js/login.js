function switchTab(tab) {
    document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.form-section').forEach(f => f.classList.remove('active'));

    if (tab === 'login') {
        document.querySelectorAll('.auth-tab')[0].classList.add('active');
        document.getElementById('login-form').classList.add('active');
    } else {
        document.querySelectorAll('.auth-tab')[1].classList.add('active');
        document.getElementById('register-form').classList.add('active');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetch('/auth/ip')
        .then(res => res.json())
        .then(data => {
            if (document.getElementById('current-ip')) {
                document.getElementById('current-ip').textContent = data.ip;
            }
        });
});
