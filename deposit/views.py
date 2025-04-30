import uuid
import requests
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .models import AgentDepositHistory
from .serializers import AgentDepositHistorySerializer

User = get_user_model()

class AgentDepositAPIView(APIView):
    permission_classes = [IsAuthenticated]  # 👈 Require authentication

    def post(self, request):
        try:
            agent = request.user

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


class AgentDepositHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]  # 👈 Require authentication

    def get(self, request):
        try:
            agent = request.user
            deposits = AgentDepositHistory.objects.filter(agent=agent).order_by('-timestamp')
            serializer = AgentDepositHistorySerializer(deposits, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response({'error': 'Server error', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
