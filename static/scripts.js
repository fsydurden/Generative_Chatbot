// Validation for Login Form
function validateForm() {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();

    if (username === "" || password === "") {
        alert("Please fill out all fields.");
        return false;
    }
    return true;
}

// Validation for Sign-Up Form
function validateSignUpForm() {
    const username = document.getElementById('signup-username').value.trim();
    const password = document.getElementById('signup-password').value.trim();
    const confirmPassword = document.getElementById('confirm-password').value.trim();

    if (username === "" || password === "" || confirmPassword === "") {
        alert("Please fill out all fields.");
        return false;
    }
    
    if (password !== confirmPassword) {
        alert("Passwords do not match.");
        return false;
    }

    if (password.length < 6) {
        alert("Password must be at least 6 characters long.");
        return false;
    }

    return true;
}
