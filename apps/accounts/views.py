from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render


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
