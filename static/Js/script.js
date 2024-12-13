document.getElementById('toggleCurrentPassword').addEventListener('click', togglePasswordVisibility.bind(null, 'currentPassword'));
document.getElementById('toggleNewPassword').addEventListener('click', togglePasswordVisibility.bind(null, 'newPassword'));
document.getElementById('toggleConfirmPassword').addEventListener('click', togglePasswordVisibility.bind(null, 'confirmPassword'));

function togglePasswordVisibility(inputId) {
    const passwordInput = document.getElementById(inputId);
    const toggleIcon = document.querySelector(`#toggle${capitalizeFirstLetter(inputId)}`);
    const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
    
    passwordInput.setAttribute('type', type);
    toggleIcon.classList.toggle('fa-eye-slash'); // Cambia la clase del icono
}

function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}


document.getElementById('changePasswordForm').addEventListener('submit', (event) => {
    event.preventDefault();
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    if (newPassword === confirmPassword) {
        alert('Contraseña cambiada exitosamente'); // Aquí puedes implementar la lógica real para cambiar la contraseña
        console.log('Formulario enviado con:', { currentPassword, newPassword });
    } else {
        alert('Las contraseñas no coinciden');
    }
});



