import uuid
import requests
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from .models import AgentDepositHistory
from .serializers import AgentDepositHistorySerializer

User = get_user_model()  # Your custom Agents model

class AgentDepositAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Determine the agent
            if request.user.is_authenticated:
                agent = request.user
            else:
                agent = User.objects.first()
                if not agent:
                    return Response({'error': 'No agent available.'}, status=status.HTTP_400_BAD_REQUEST)

            user_email = request.data.get('email')
            amount = request.data.get('amount')

            if not user_email or not amount:
                return Response({'error': 'Email and amount are required.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                amount = Decimal(str(amount))
            except (ValueError, Decimal.InvalidOperation):
                return Response({'error': 'Amount must be a valid number.'}, status=status.HTTP_400_BAD_REQUEST)

            if agent.current_balance < amount:
                return Response({'error': 'Insufficient balance.'}, status=status.HTTP_400_BAD_REQUEST)

            transaction_id = uuid.uuid4().hex[:12].upper()

            external_payload = {
                'email': user_email,
                'amount': str(amount),
                'transaction_id': transaction_id
            }

            response = requests.post(
                'https://mtima.onrender.com/api/v1/dpst/',
                json=external_payload
            )

            if response.status_code == 201:
                AgentDepositHistory.objects.create(
                    agent=agent,
                    user_email=user_email,
                    amount=amount,
                    transaction_id=transaction_id
                )
                agent.current_balance -= amount
                agent.save()

                return Response({
                    'message': 'Deposit successful',
                    'transaction_id': transaction_id,
                    'amount': str(amount)
                }, status=status.HTTP_201_CREATED)

            else:
                error_details = response.json() if response.headers.get('Content-Type') == 'application/json' else response.text
                return Response({
                    'error': 'Failed to deposit to user',
                    'details': error_details
                }, status=response.status_code)

        except requests.exceptions.RequestException as e:
            return Response({'error': 'External API error', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({'error': 'Server error', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExternalAgentDepositAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            agent_code = request.data.get('agent_code')
            amount = request.data.get('amount')
            transaction_id = request.data.get('transaction_id')

            if not agent_code or not amount or not transaction_id:
                return Response({'error': 'agent_code, amount, and transaction_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                amount = Decimal(str(amount))
            except (ValueError, Decimal.InvalidOperation):
                return Response({'error': 'Amount must be numeric.'}, status=status.HTTP_400_BAD_REQUEST)

            agent = User.objects.filter(agent_code=agent_code).first()
            if not agent:
                return Response({'error': 'Invalid agent code.'}, status=status.HTTP_404_NOT_FOUND)

            agent.current_balance += amount
            agent.save()

            AgentDepositHistory.objects.create(
                agent=agent,
                user_email=None,
                amount=amount,
                transaction_id=transaction_id
            )

            return Response({
                'message': 'Agent credited successfully.',
                'agent_code': agent_code,
                'amount': str(amount)
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': 'Server error', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AgentDepositHistoryAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({'error': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)

            agent = request.user
            deposits = AgentDepositHistory.objects.filter(agent=agent).order_by('-timestamp')
            serializer = AgentDepositHistorySerializer(deposits, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response({'error': 'Server error', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
