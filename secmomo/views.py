from django.shortcuts import render
from decimal import Decimal
from rest_framework import status # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.decorators import api_view # type: ignore
from secmomo.serializers import ChangePasswordSerializer
from .serializers import AgentSerializer
from rest_framework.authtoken.models import Token # type: ignore
from django.contrib.auth import authenticate
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.authtoken.models import Token # type: ignore
from rest_framework.decorators import api_view, permission_classes # type: ignore
from rest_framework.permissions import IsAuthenticated # type: ignore
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import get_object_or_404
from .models import Agents
from django.conf import settings  # Import settings
from django.shortcuts import redirect #for redirection
from .models import IdentityVerification #identity verification
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Transaction  # Import the Transaction model
from django.shortcuts import get_object_or_404

# Create your views here.
#for registering agents
@api_view(['POST'])
def register_agent(request):
    if request.method == 'POST':
        serializer = AgentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
#handling login
@api_view(['POST', 'GET'])
def agent_login(request):
    if request.method == 'POST':
        username = request.data.get('username')
        password = request.data.get('password')

        user = None
        if '@' in username:
            try:
                user = Agents.objects.get(email=username)
            except ObjectDoesNotExist:
                pass

        if not user:
            user = authenticate(username=username, password=password)

        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': token.key}, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
#handling logout
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agent_logout(request):
    if request.method == 'POST':
        try:
            # Delete the user's token to logout
            request.user.auth_token.delete()
            return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
#handling password reseting
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    if request.method == 'POST':
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.check_password(serializer.data.get('old_password')):
                user.set_password(serializer.data.get('new_password'))
                user.save()
                update_session_auth_hash(request, user)  # To update session after password change
                return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
            return Response({'error': 'Incorrect old password.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
 #Trasactions views   
@permission_classes([IsAuthenticated])
@api_view(['GET'])
def agent_transaction_history(request):
    
    #This is for handling th esginet verification////////////////////////////////////
    user = request.user
    verification = IdentityVerification.objects.get(user=user)

    if not verification.is_verified:
        return Response({"error": "Please verify your identity before making a deposit."}, status=status.HTTP_403_FORBIDDEN)
    #//////////////////////////////////////////////////////////////////////////////
    
    agent = request.user
    transactions = Transaction.objects.filter(agent=agent)

    if not transactions:
        return Response({"message": "No transactions found for this agent."}, status=status.HTTP_404_NOT_FOUND)

    transaction_data = [
        {
            "date": transaction.date,
            "amount": str(transaction.amount),
            "transaction_type": transaction.transaction_type,
        }
        for transaction in transactions
    ]

    return Response(transaction_data, status=status.HTTP_200_OK)

#handle diposit
@permission_classes([IsAuthenticated])
@api_view(['POST'])
def agent_deposit(request):
    """
    API endpoint for agents to deposit money.
    """
    #This is for handling th esginet verification/////////////////////////////
    user = request.user
    verification = IdentityVerification.objects.get(user=user)

    if not verification.is_verified:
        return Response({"error": "Please verify your identity before making a deposit."}, status=status.HTTP_403_FORBIDDEN)
    #//////////////////////////////////////////////////////////////////////
    try:
        data = request.data  # DRF handles JSON parsing automatically
        agent_code = data.get("agent_code")
        amount = data.get("amount")

        # Validate agent_code
        if not agent_code:
            return Response({"error": "Agent code is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if agent exists
        try:
            agent = Agents.objects.get(agent_code=agent_code)
        except Agents.DoesNotExist:
            return Response({"error": "Invalid agent code"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate amount
        if amount is None:
            return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure amount is a valid decimal
        try:
            amount = Decimal(amount)
            if amount <= 0:
                return Response({"error": "Amount must be greater than zero"}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, InvalidOperation):
            return Response({"error": "Invalid amount value"}, status=status.HTTP_400_BAD_REQUEST)

        # Add amount to agent's balance
        agent.balance += amount
        agent.save()

        # Record the transaction in the Transaction model
        Transaction.objects.create(agent=agent, amount=amount, transaction_type='deposit')

        return Response({"message": "Deposit successful", "new_balance": str(agent.balance)}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
 
 #handle verification identity   
@permission_classes([IsAuthenticated])
@api_view(['POST'])
def verify_identity(request):
    """
    Redirects the user to the e-Signet verification page.
    """
    user = request.user
    verification, created = IdentityVerification.objects.get_or_create(user=user)

    if verification.is_verified:
        return Response({"message": "Identity already verified."}, status=status.HTTP_200_OK)

    # Redirect to e-Signet for verification
    return redirect(f"https://esignet.example.com/verify?user_id={user.id}")  # Replace with actual e-Signet URL

@api_view(['GET'])
def e_signet_callback(request):
    user_id = request.GET.get('user_id')
    verification_result = request.GET.get('verification_result')  # This should be set by e-Signet

    try:
        user = Agents.objects.get(id=user_id)
        verification, created = IdentityVerification.objects.get_or_create(user=user)

        if verification_result == 'success':
            verification.is_verified = True
            verification.save()
            return redirect(reverse('agent_withdraw'))  # Redirect to withdrawal form
        else:
            return Response({"error": "Verification failed."}, status=status.HTTP_403_FORBIDDEN)
    except Agents.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
    
#Handle withdraw
@permission_classes([IsAuthenticated])
@api_view(['POST'])
def agent_withdraw(request):
    
    #This is for handling th esginet verification/////////////////////////////
    user = request.user
    verification = IdentityVerification.objects.get(user=user)

    if not verification.is_verified:
        return Response({"error": "Please verify your identity before making a withdrawal."}, status=status.HTTP_403_FORBIDDEN)
    #////////////////////////////////////////////////////////////////////////////
    
    # Proceed with withdrawal logic...
    try:
        data = request.data
        amount = Decimal(data.get("amount"))
        if amount <= 0:
            return Response({"error": "Amount must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)

        # Check agent balance and deduct
        agent = request.user
        if agent.balance < amount:
            return Response({"error": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)

        agent.balance -= amount
        agent.save()
        Transaction.objects.create(agent=agent, amount=amount, transaction_type='withdrawal')

        return Response({"message": "Withdrawal successful", "new_balance": str(agent.balance)}, status=status.HTTP_200_OK)

    except (ValueError, InvalidOperation):
        return Response({"error": "Invalid amount value."}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
