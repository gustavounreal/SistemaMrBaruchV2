from django.http import JsonResponse
from django.contrib.auth import get_user_model

def buscar_captador(request, captador_id):
    User = get_user_model()
    try:
        user = User.objects.get(id=captador_id)
        return JsonResponse({
            'success': True,
            'nome': user.get_full_name() or user.username,
            'email': user.email
        })
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Captador não encontrado.'})
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as django_logout
from django.views.decorators.http import require_POST
from .serializers import GoogleAuthSerializer, UserSerializer
from .forms import LoginForm, RegisterForm, AtendenteForm, PerfilAtendenteForm
from .models import DadosUsuario

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    """Autenticação via Google"""
    serializer = GoogleAuthSerializer(data=request.data)

    if serializer.is_valid():
        token_data = serializer.validated_data['token']

        email = token_data.get('email')
        google_id = token_data.get('sub')
        first_name = token_data.get('given_name', '')
        last_name = token_data.get('family_name', '')
        avatar_url = token_data.get('picture', '')

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'google_id': google_id,
                'first_name': first_name,
                'last_name': last_name,
                'avatar_url': avatar_url,
                'username': email.split('@')[0],
                'ativo': True
            }
        )

        if not created:
            user.google_id = google_id
            user.avatar_url = avatar_url
            user.save()

        refresh = RefreshToken.for_user(user)
        refresh.set_exp(lifetime=timedelta(hours=16))

        return Response({
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': UserSerializer(user).data
        })

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    """Login tradicional via API - aceita email ou username"""
    print("="*80)
    print("🔐 LOGIN_API CHAMADO")
    print(f"Method: {request.method}")
    print(f"Data: {request.data}")
    print("="*80)
    
    email = request.data.get('email')  # Pode ser email OU username
    password = request.data.get('password')
    remember_me = request.data.get('remember_me', False)

    if not email or not password:
        return Response({'error': 'E-mail/usuário e senha são obrigatórios'}, status=status.HTTP_400_BAD_REQUEST)

    # Usa authenticate que aceita email OU username via EmailBackend
    user = authenticate(request, username=email, password=password)
    
    print(f"Authenticate result: {user}")

    if user:
        if user.ativo:
            refresh = RefreshToken.for_user(user)
            refresh.set_exp(lifetime=timedelta(hours=16))
            
            print(f"✅ Login bem-sucedido: {user.username}")

            response = Response({
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': UserSerializer(user).data
            })
            
            # Configurar cookies HTTP com os tokens
            response.set_cookie(
                'access_token',
                str(refresh.access_token),
                max_age=60*60,  # 1 hora
                httponly=True,
                secure=False,  # True em produção com HTTPS
                samesite='Lax'
            )
            response.set_cookie(
                'refresh_token',
                str(refresh),
                max_age=60*60*16,  # 16 horas
                httponly=True,
                secure=False,  # True em produção com HTTPS
                samesite='Lax'
            )
            
            return response
        else:
            print(f"❌ Conta desativada: {user.username}")
            return Response({'error': 'Conta desativada'}, status=status.HTTP_401_UNAUTHORIZED)
    else:
        print(f"❌ Credenciais inválidas para: {email}")
        return Response({'error': 'E-mail/usuário ou senha incorretos'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_api(request):
    """Registro via API"""
    form = RegisterForm(data=request.data)

    if form.is_valid():
        user = form.save()
        refresh = RefreshToken.for_user(user)
        refresh.set_exp(lifetime=timedelta(hours=16))

        return Response({
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': UserSerializer(user).data,
            'message': 'Conta criada com sucesso!'
        }, status=status.HTTP_201_CREATED)

    return Response({'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)


def login_page(request):
    login_form = LoginForm()
    register_form = RegisterForm()

    # Se o usuário já estiver autenticado, redireciona conforme grupo
    if request.user.is_authenticated:
        user = request.user
        # Evita redirect loop: só redireciona se não estiver já na página destino
        if user.groups.filter(name='atendente').exists() and request.path != '/atendimento/area-de-trabalho/':
            return redirect('atendimento:area_de_trabalho_atendente')
        if user.groups.filter(name='admin').exists() and request.path != '/accounts/dashboard/':
            return redirect('accounts:dashboard')

    return render(request, 'accounts/login.html', {
        'login_form': login_form,
        'register_form': register_form
    })

@login_required(login_url='/accounts/login/')
def dashboard_view(request):
    """Dashboard principal - aceita tanto sessão quanto JWT"""
    
    # Buscar dados reais do banco de dados
    from financeiro.models import ClienteAsaas, Comissao
    from vendas.models import Venda
    from marketing.models import Lead
    
    # Data atual e início do mês
    agora = timezone.now()
    inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Clientes Ativos (ClienteAsaas com status ativo)
    try:
        clientes_count = ClienteAsaas.objects.filter(
            Q(ativo=True) | Q(ativo__isnull=True)  # Considera ativos se campo for True ou NULL
        ).count()
    except Exception:
        clientes_count = 0
    
    # 2. Vendas do Mês (soma do valor total das vendas criadas este mês)
    try:
        vendas_mes = Venda.objects.filter(
            data_venda__gte=inicio_mes,
            data_venda__lte=agora
        ).aggregate(total=Sum('valor_total'))['total'] or 0
    except Exception:
        vendas_mes = 0
    
    # 3. Atendimentos (leads criados este mês)
    try:
        atendimentos_count = Lead.objects.filter(
            data_cadastro__gte=inicio_mes,
            data_cadastro__lte=agora
        ).count()
    except Exception:
        atendimentos_count = 0
    
    # 4. Comissões (soma das comissões pagas ou a pagar este mês)
    try:
        comissoes_valor = Comissao.objects.filter(
            data_venda__gte=inicio_mes,
            data_venda__lte=agora
        ).aggregate(total=Sum('valor_comissao'))['total'] or 0
    except Exception:
        comissoes_valor = 0

    context = {
        'user': request.user,
        'clientes_count': clientes_count,
        'vendas_mes': vendas_mes,
        'atendimentos_count': atendimentos_count,
        'comissoes_valor': comissoes_valor,
    }

    return render(request, 'accounts/dashboard.html', context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """Perfil do usuário"""
    if not request.user.is_authenticated:
        return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
    
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_api(request):
    """Logout via API"""
    try:
        refresh_token = request.data.get('refresh_token')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Logout realizado com sucesso'})
    except Exception:
        return Response({'error': 'Token inválido'}, status=status.HTTP_400_BAD_REQUEST)


@login_required
def perfil_atendente(request):
    user = request.user
    try:
        dados_usuario = user.dados
    except DadosUsuario.DoesNotExist:
        dados_usuario = None

    if request.method == 'POST':
        user_form = PerfilAtendenteForm(request.POST, instance=user)
        atendente_form = AtendenteForm(request.POST, instance=dados_usuario)

        if user_form.is_valid() and atendente_form.is_valid():
            user = user_form.save(commit=False)
            nome_completo = user_form.cleaned_data.get('nome_completo')
            if nome_completo:
                nomes = nome_completo.split(' ', 1)
                user.first_name = nomes[0]
                user.last_name = nomes[1] if len(nomes) > 1 else ''
            user.save()

            atendente = atendente_form.save(commit=False)
            atendente.user = user
            atendente.save()
            return redirect('accounts:perfil_atendente')
    else:
        user_form = PerfilAtendenteForm(instance=user, initial={
            'nome_completo': f"{user.first_name} {user.last_name}".strip()
        })
        atendente_form = AtendenteForm(instance=dados_usuario)

    return render(request, 'accounts/perfil_atendente.html', {
        'user_form': user_form,
        'atendente_form': atendente_form
    })



@require_POST
def logout_session(request):
    """Encerra a sessão do Django (session auth)."""
    if request.method == 'POST':
        django_logout(request)
        # Criar resposta de redirect
        response = redirect('accounts:login')
        # Limpar cookies do JWT
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        # Limpar header de autorização se existir
        if 'HTTP_AUTHORIZATION' in request.META:
            del request.META['HTTP_AUTHORIZATION']
        return response
    return JsonResponse({'error': 'Método não permitido'}, status=405)
