from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render

from .models import User


def login_view(request):
    error = ''
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        error = 'Email o contrasena incorrectos'

    return render(request, 'accounts/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')


def forgot_password(request):
    enviado = False
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        user = User.objects.filter(email=email, is_active=True).first()
        if user:
            # Generar token y nueva contraseña temporal
            import secrets
            new_password = secrets.token_urlsafe(8)
            user.set_password(new_password)
            user.save()
            # En producción enviaría email. Por ahora mostramos en pantalla.
            messages.success(request, f'Nueva contrasena generada: {new_password} — Anotala y cambiala desde tu perfil.')
        else:
            messages.info(request, 'Si el email existe, se genero una nueva contrasena.')
        enviado = True

    return render(request, 'accounts/forgot_password.html', {'enviado': enviado})
