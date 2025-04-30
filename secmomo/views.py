import time
import random
import string
import logging
import requests
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.authtoken.models import Token
from django.contrib.auth import update_session_auth_hash
from .models import Agents, AgentApplication
from .serializers import (
    AgentSerializer,
    AgentLoginSerializer,
    ChangePasswordSerializer,
    AgentProfileSerializer,
    SimpleAgentApplicationSerializer
)

logger = logging.getLogger(__name__)
MINIMUM_BALANCE = 100000  # 200,000 MWK

# Helper function for balance retrieval
def get_user_balance(email, auth_token):
    """Retrieve user balance from main backend"""
    try:
        response = requests.post(
            'https://mtima.onrender.com/api/v1/accounts/get-balance/',
            json={'email': email},
            headers={'Authorization': f'Bearer {auth_token}'},
            timeout=5
        )
        response.raise_for_status()
        return float(response.json().get('balance', 0))
    except requests.exceptions.RequestException as e:
        logger.error(f"Balance retrieval failed: {str(e)}")
        raise

# Agent Registration
@api_view(['POST'])
def register_agent(request):
    """Register a new agent account (pending approval)"""
    serializer = AgentSerializer(data=request.data)
    if serializer.is_valid():
        agent = serializer.save()
        
        # Send approval request to admin
        send_mail(
            'New Agent Registration',
            f'New agent {agent.email} needs approval.\n\n'
            f'Review: {request.build_absolute_uri(reverse("admin:agents_agent_change", args=[agent.id]))}',
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            fail_silently=False,
        )
        
        return Response({
            'message': 'Registration successful. Pending approval.',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Agent Login
@api_view(['POST'])
def agent_login(request):
    """Authenticate agent and return token"""
    serializer = AgentLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': {
                'email': user.email,
                'agent_code': user.agent_code,
                'balance': user.current_balance
            }
        })
    return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

# Auto-Approval Endpoint
@api_view(['POST'])
def auto_approve_agent(request):
    try:
        serializer = SimpleAgentApplicationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        username = serializer.validated_data['username']
        phone_number = serializer.validated_data['phone_number']
        balance = float(request.data.get('balance', 0))

        ## Check for existing email
        if Agents.objects.filter(email=email).exists():
            return Response(
                {'error': 'Email already registered.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify minimum balance
        if balance < MINIMUM_BALANCE:
            AgentApplication.objects.create(
                username=username,
                email=email,
                phone_number=phone_number,
                status='rejected',
                verification_notes=f"Balance {balance} > {MINIMUM_BALANCE}"
            )
            return Response(
                {'error': f'Minimum balance not met (requires {MINIMUM_BALANCE} MWK)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate credentials
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        agent_code = ''.join(random.choices(string.digits, k=5))

        # Create records
        with transaction.atomic():
            agent = Agents.objects.create_user(
                username=username,
                email=email,
                password=temp_password,
                phone_number=phone_number,
                agent_code=agent_code,
                current_balance=balance,
                status='active',
                is_active=True
            )
            
            AgentApplication.objects.create(
                username=username,
                email=email,
                phone_number=phone_number,
                status='approved',
                reviewed_at=timezone.now()
            )

        # Send credentials
        login_url = 'https://pamomo-agent.netlify.app'  # Update with your frontend URL
        email_body = f"""Dear {username},

We are pleased to inform you that your agent application has been approved!

Your agent details: 
- Username: {username}
- Agent Code: {agent_code}
- Password: {temp_password}

Please login to the agent portal using the following link:
{ login_url }

For security reasons, you MUST change your temporary password immediately after logging in.
Welcome to our agent network!

Best regards,
The Secure MoMo Team"""

        send_mail(
            'Agent Account Approved',
            email_body,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False
        )

        return Response({
            'status': 'approved',
            'username': username,
            'agent_code': agent_code,
            'email': email,
            'balance': balance
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Approval error: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
# Agent Profile
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agent_profile(request):
    """Get current agent's profile"""
    serializer = AgentProfileSerializer(request.user)
    return Response(serializer.data)

# Change Password
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change agent password"""
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        if user.check_password(serializer.data.get('old_password')):
            user.set_password(serializer.data.get('new_password'))
            user.save()
            update_session_auth_hash(request, user)
            return Response({'message': 'Password updated'})
        return Response({'error': 'Incorrect password'}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Admin Approval Endpoint
@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_approve_agent(request, agent_id):
    """Manual approval by admin"""
    application = get_object_or_404(AgentApplication, id=agent_id)
    
    if application.status != 'pending':
        return Response(
            {'error': 'Already processed'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Generate credentials
    temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    agent_code = ''.join(random.choices(string.digits, k=5))

    # Create agent
    agent = Agents.objects.create_user(
        username=application.email,
        email=application.email,
        password=temp_password,
        phone_number=application.phone_number,
        agent_code=agent_code,
        status='active'
    )

    # Update application
    application.status = 'approved'
    application.reviewed_by = request.user
    application.reviewed_at = timezone.now()
    application.save()

    # Send email
    send_mail(
        'Agent Account Approved',
        f'Your agent code: {agent_code}\nTemp password: {temp_password}',
        settings.DEFAULT_FROM_EMAIL,
        [application.email],
        fail_silently=False
    )

    return Response({
        'agent_code': agent_code,
        'email': application.email
    })

# Agent Logout
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agent_logout(request):
    """Invalidate auth token"""
    request.user.auth_token.delete()
    return Response({'message': 'Logged out successfully'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_agent_username(request):
    """Get agent username by agent code"""
    agent_code = request.query_params.get('agent_code')

    if not agent_code:
        return Response({'error': 'Agent code is required'}, status=status.HTTP_400_BAD_REQUEST)

    agent = get_object_or_404(Agents, agent_code=agent_code)
    return Response({'username': agent.username}, status=status.HTTP_200_OK)



#handling get balance on frontend of an logged in agent
#@api_view(['POST'])
#@permission_classes([IsAuthenticated])
#def get_balance(request):
  #  """
  #  Return the current balance of the authenticated agent.
  #  """
  #  agent = request.user
   # return Response({
  #      'agent_code': agent.agent_code,
  #      'balance': agent.current_balance
 #   })

#handle get balance
@api_view(['POST'])
#@permission_classes([IsAuthenticated])
def get_balance(request):
    """
    Return the current balance for the given agent code.
    """
    agent_code = request.data.get('agent_code')

    if not agent_code:
        return Response({'error': 'Agent code is required'}, status=400)

    try:
        agent = Agents.objects.get(agent_code=agent_code)
        return Response({
            'balance': agent.current_balance
        }, status=200)
    except Agents.DoesNotExist:
        return Response({'error': 'Agent not found'}, status=404)
