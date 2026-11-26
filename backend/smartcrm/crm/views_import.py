from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
import pandas as pd
from .models import Customer
from django.db import transaction

class CustomerBulkImportView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        if not file_obj.name.endswith('.xlsx'):
            return Response({"error": "File must be an Excel (.xlsx) file"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Read Excel file
            df = pd.read_excel(file_obj, engine='openpyxl')
            
            # Normalize column names (strip spaces, lowercase)
            df.columns = [c.strip().lower() for c in df.columns]

            required_columns = ['customer name', 'phone']
            missing_cols = [col for col in required_columns if col not in df.columns]
            
            if missing_cols:
                return Response(
                    {"error": f"Missing required columns: {', '.join(missing_cols)}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Process rows
            created_count = 0
            skipped_count = 0
            errors = []

            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        name = str(row['customer name']).strip()
                        if not name or pd.isna(name):
                            continue

                        # Generate or read valid data
                        phone = str(row['phone']).strip()
                        if not phone or pd.isna(row['phone']):
                           # Skip if phone is empty/NaN as it is now mandatory per row logic too
                           continue
                           
                        email = str(row['email']).strip() if 'email' in df.columns and not pd.isna(row['email']) else ""
                        
                        # Handle outstanding
                        outstanding = "₹0.00"
                        if 'outstanding' in df.columns and not pd.isna(row['outstanding']):
                            val = row['outstanding']
                            # If it's a number, format it
                            if isinstance(val, (int, float)):
                                outstanding = f"₹{val:.2f}"
                            else:
                                outstanding = str(val).strip()

                        # Optional Code
                        code = None
                        if 'code' in df.columns and not pd.isna(row['code']):
                            code_val = str(row['code']).strip()
                            if code_val:
                                code = code_val
                        
                        # Auto-generate code if missing
                        if not code:
                            # Simple generation strategy: CUST-{max_id + 1}
                            last_cust = Customer.objects.order_by('-id').first()
                            last_id = last_cust.id if last_cust else 0
                            current_id_guess = last_id + created_count + 1
                            code = f"CUST-{1000 + current_id_guess}"

                        # Check if customer exists by name, code or PHONE
                        exists = False
                        if code:
                             if Customer.objects.filter(code=code).exists():
                                 exists = True
                        
                        # Check phone existence (Critical requirement)
                        if not exists and phone:
                            if Customer.objects.filter(phone=phone).exists():
                                exists = True

                        # Fallback to name check if no code provided
                        if not exists and not code:
                             if Customer.objects.filter(name__iexact=name).exists():
                                 exists = True
                        
                        if exists:
                            skipped_count += 1
                            continue

                        # Create
                        Customer.objects.create(
                            name=name,
                            phone=phone,
                            email=email,
                            outstanding=outstanding,
                            code=code  # If None, model might auto-generate or stay null depending on logic
                        )
                        created_count += 1

                    except Exception as e:
                        errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                "message": "Import processing complete",
                "created": created_count,
                "skipped": skipped_count,
                "errors": errors[:10]  # Return top 10 errors
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Failed to process file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
