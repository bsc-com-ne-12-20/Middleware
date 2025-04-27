from django.shortcuts import get_object_or_404
from rest_framework.response import Response
<<<<<<< HEAD
from rest_framework import generics, status

from deposit.models import AgentDepositHistory
from secmomo.models import Agents
from .serializers import AgentDepositHistorySerializer, AgentDepositSerializer

class AgentDepositAPIView(generics.CreateAPIView):
    serializer_class = AgentDepositSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
=======
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
>>>>>>> 53f607d (Remove external deposit api in deposit agent)

        result = serializer.save()  # ✅ Get the return value from create()
        return Response(result, status=status.HTTP_201_CREATED)

class AgentDepositHistoryAPIView(generics.ListAPIView):
    serializer_class = AgentDepositHistorySerializer
    permission_classes = []  # Allow anonymous access

    def get_queryset(self):
        agent_code = self.request.query_params.get("agent_code")  # Get agent code from the URL query parameter

        if not agent_code:
            return AgentDepositHistory.objects.none()  # If no agent code is provided, return no data

<<<<<<< HEAD
        # Fetch the agent based on the provided agent code
        agent = get_object_or_404(Agents, agent_code=agent_code)
        
        # Return the deposit history for that agent, ordered by timestamp
        return AgentDepositHistory.objects.filter(agent=agent).order_by('-timestamp')
=======
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
>>>>>>> 53f607d (Remove external deposit api in deposit agent)
