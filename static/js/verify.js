document.addEventListener('DOMContentLoaded', () => {
    fetch('/auth/ip')
        .then(res => res.json())
        .then(data => {
            const ipElem = document.getElementById('current-ip');
            if (ipElem) {
                ipElem.textContent = data.ip;
            }
        });
});
