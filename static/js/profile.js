function switchSettingsTab(tabName) {
    document.querySelectorAll('.settings-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tabName}`).classList.add('active');

    // Find nav item by text or icon, or just rely on the click event if passed
    // But since we call this from onclick, we can use event.currentTarget if available
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Profile Update
    const profileBtn = document.querySelector('#tab-profile .btn-primary');
    if (profileBtn) {
        profileBtn.addEventListener('click', async () => {
            const fullName = document.getElementById('p_fullname').value;
            const phone = document.getElementById('p_phone').value;
            const gender = document.getElementById('p_gender').value;
            const bio = document.getElementById('p_bio').value;

            try {
                const res = await fetch('/api/profile/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        full_name: fullName,
                        phone_number: phone,
                        gender: gender,
                        bio: bio
                    })
                });
                const data = await res.json();
                alert(data.message);
            } catch (e) {
                alert("Update failed");
            }
        });
    }

    // Security Update
    const securityBtn = document.querySelector('#tab-security .btn-outline'); // Update password btn
    if (securityBtn) {
        securityBtn.addEventListener('click', () => {
            const modal = document.getElementById('password-modal');
            if (modal) {
                modal.style.display = 'flex';
                // Clear fields
                document.getElementById('m_current_pass').value = '';
                document.getElementById('m_new_pass').value = '';
                document.getElementById('m_confirm_pass').value = '';
            }
        });
    }

    window.submitPasswordChange = async function () {
        const current = document.getElementById('m_current_pass').value;
        const newPass = document.getElementById('m_new_pass').value;
        const confirmPass = document.getElementById('m_confirm_pass').value;

        if (!current || !newPass || !confirmPass) {
            alert("Please fill all fields");
            return;
        }

        try {
            const res = await fetch('/api/profile/security', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_password: current,
                    new_password: newPass,
                    confirm_password: confirmPass
                })
            });
            const data = await res.json();
            alert(data.message || data.detail);
            if (res.ok) {
                document.getElementById('password-modal').style.display = 'none';
            }
        } catch (e) {
            alert("Error updating password");
        }
    }

    // 2FA Toggle (Security Tab)
    const twoFaToggle = document.querySelector('#tab-security input[type="checkbox"]');
    if (twoFaToggle) {
        twoFaToggle.addEventListener('change', savePreferences);
    }

    // Preferences Toggles
    const prefToggles = document.querySelectorAll('#tab-preferences input[type="checkbox"]');
    prefToggles.forEach(t => t.addEventListener('change', savePreferences));

    async function savePreferences() {
        const darkMode = document.querySelectorAll('#tab-preferences input[type="checkbox"]')[0].checked;
        const tradeSounds = document.querySelectorAll('#tab-preferences input[type="checkbox"]')[1].checked;
        const twoFa = document.querySelector('#tab-security input[type="checkbox"]').checked;

        try {
            await fetch('/api/profile/preferences', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    dark_mode: darkMode,
                    notifications: true, // Default
                    email_reports: false, // Default
                    trade_sounds: tradeSounds,
                    two_factor_auth: twoFa
                })
            });
            // console.log("Preferences saved");
        } catch (e) {
            console.error("Failed to save preferences");
        }
    }
});

async function confirmDeleteAccount() {
    if (!confirm("Are you absolutely sure you want to delete your account? This action is irreversible and will delete all your data, wallets, and settings.")) {
        return;
    }

    const password = prompt("Please enter your password to confirm deletion:");
    if (!password) return;

    try {
        const response = await fetch('/auth/delete_account', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: password })
        });

        const data = await response.json();

        if (response.ok) {
            alert("Account deleted successfully. You will be redirected to the login page.");
            window.location.href = '/auth/login';
        } else {
            alert("Error: " + data.detail);
        }
    } catch (e) {
        alert("Request failed");
    }
}
